"""FastAPI application entry point.

使用 config 模块统一管理配置和服务实例
"""
import os
from dotenv import load_dotenv

# 在导入其他模块之前加载 .env 文件
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import upload, ingest, graph, settings, knowledge_card, qa, evaluation
from infra.neo4j_client import neo4j_client
from infra.faiss_store import faiss_store
from config import settings as config_settings
from config.instances import initialize_instances

# 验证配置
config_errors = config_settings.validate()
if config_errors:
    print("=== 配置验证失败 ===")
    for error in config_errors:
        print(f"❌ {error}")
    print("=" * 50)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    print("\n=== 服务启动 ===")
    
    # Startup: Initialize all instances
    try:
        initialize_instances()
        print("✅ All instances initialized successfully")
    except Exception as e:
        print(f"⚠️  Failed to initialize instances: {e}")
    
    # Startup: Initialize Neo4j connection
    try:
        neo4j_client.initialize()
        print("✅ Neo4j client initialized successfully")
    except Exception as e:
        print(f"⚠️  Failed to initialize Neo4j client: {e}")
        print("   The API will start but database operations will fail.")
    
    # Startup: Initialize FAISS
    if config_settings.faiss_enabled:
        try:
            faiss_store.load_index()
            print(f"✅ FAISS index loaded from {config_settings.faiss_index_path}")
        except Exception as e:
            print(f"⚠️  FAISS index not found or failed to load: {e}")
            print("   Starting with empty FAISS index")
    
    # 打印配置摘要
    print(f"\n=== 配置摘要 ===")
    print(f"AI Provider: {config_settings.ai_provider}")
    print(f"Embedding Model: {config_settings.embedding_model}")
    print(f"FAISS Enabled: {config_settings.faiss_enabled}")
    print(f"Debug Mode: {config_settings.debug_mode}")
    
    yield
    
    # Shutdown: Close connections
    print("\n=== 服务关闭 ===")
    
    if neo4j_client.driver:
        neo4j_client.close()
        print("✅ Neo4j client closed")
    
    # Shutdown: Save FAISS index
    if config_settings.faiss_enabled:
        try:
            faiss_store.save_index()
            print("✅ FAISS index saved")
        except Exception as e:
            print(f"⚠️  Failed to save FAISS index: {e}")


# Create FastAPI app
app = FastAPI(
    title="GraphRAG Knowledge Service API",
    description="面向《软件工程》课程的多模态知识服务平台",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router)
app.include_router(ingest.router)
app.include_router(graph.router)
app.include_router(settings.router)
app.include_router(knowledge_card.router)
app.include_router(qa.router)
app.include_router(evaluation.router)


@app.get("/")
async def root():
    """Root endpoint - return API information."""
    return {
        "service": "GraphRAG Knowledge Service API",
        "version": "2.0.0",
        "description": "面向《软件工程》课程的多模态知识服务平台",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": "2026-04-16"
    }


@app.get("/config")
async def get_config_summary():
    """Get configuration summary."""
    return {
        "ai_provider": config_settings.ai_provider,
        "embedding_model": config_settings.embedding_model,
        "faiss_enabled": config_settings.faiss_enabled,
        "faiss_index_type": config_settings.faiss_index_type
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )