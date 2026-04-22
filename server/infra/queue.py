"""Redis Queue (RQ) configuration and utilities."""
import redis
import os
from typing import Optional, Dict, Any, List

# Windows 不支持 os.fork()，RQ Worker 无法工作，使用优雅降级
IS_WINDOWS = os.name == 'nt'

if not IS_WINDOWS:
    from rq import Queue, Connection, Worker
    from rq.job import Job
    from rq import get_current_job
    RQ_AVAILABLE = True
else:
    RQ_AVAILABLE = False
    Queue = None
    Connection = None
    Worker = None
    Job = None
    get_current_job = None


class RedisQueue:
    """Redis Queue client wrapper."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis connection and RQ queue.
        
        Args:
            redis_url: Redis connection URL (defaults to settings.redis_url)
        """
        from infra.config import settings
        self.redis_url = redis_url or settings.redis_url
        
        # Windows 系统不支持 RQ，直接使用内存存储
        if IS_WINDOWS:
            print("[WARN] Windows system does not support RQ (os.fork), using in-memory task queue")
            self._connected = False
            self.redis_conn = None
            self.queue = None
            return
        
        try:
            # Parse Redis URL
            self.redis_conn = redis.from_url(self.redis_url)
            # Test connection
            self.redis_conn.ping()
            
            # Create RQ queue
            self.queue = Queue(connection=self.redis_conn, name='default')
            self._connected = True
        except Exception as e:
            print(f"⚠️  Redis connection failed: {e}")
            print("   Falling back to in-memory job storage")
            self._connected = False
            self.redis_conn = None
            self.queue = None
    
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected
    
    def enqueue(self, func, *args, **kwargs) -> Optional[Job]:
        """
        Enqueue a job.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Job instance or None if Redis is not connected
        """
        if not self._connected:
            return None
        
        try:
            if 'timeout' not in kwargs:
                kwargs['timeout'] = '1h'
            job = self.queue.enqueue(func, *args, **kwargs)
            return job
        except Exception as e:
            print(f"⚠️  Failed to enqueue job: {e}")
            return None
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get a job by ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job instance or None
        """
        if not self._connected or Job is None:
            return None
        
        try:
            return Job.fetch(job_id, connection=self.redis_conn)
        except Exception:
            return None
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get job status information.
        
        Args:
            job_id: Job ID
            
        Returns:
            Dictionary with job status information
        """
        if not self._connected:
            return {
                "status": "unknown",
                "error": "Redis not connected"
            }
        
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            
            # Map RQ job status to our status format
            status_map = {
                'queued': 'queued',
                'started': 'processing',
                'finished': 'completed',
                'failed': 'failed',
                'deferred': 'queued',
                'scheduled': 'queued',
                'canceled': 'cancelled'
            }
            
            result = {
                "status": status_map.get(job.get_status(), 'unknown'),
                "jobId": job.id,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "ended_at": job.ended_at.isoformat() if job.ended_at else None,
            }
            
            # Add result if completed
            if job.is_finished:
                result["result"] = job.result
            
            # Add error if failed
            if job.is_failed:
                result["error"] = str(job.exc_info) if job.exc_info else "Unknown error"
            
            # Try to get custom metadata (progress, message, etc.)
            if hasattr(job, 'meta') and job.meta:
                result.update(job.meta)
            
            return result
            
        except Exception as e:
            return {
                "status": "not_found",
                "error": str(e)
            }
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job.
        
        Args:
            job_id: Job ID to cancel
            
        Returns:
            True if job was cancelled, False otherwise
        """
        if not self._connected:
            return False
        
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            
            # Check if job is still queued or processing
            if job.get_status() in ['queued', 'started', 'deferred', 'scheduled']:
                # Set cancel flag in metadata for running jobs
                if job.get_status() == 'started':
                    meta = job.meta or {}
                    meta['_cancelled'] = True
                    meta['status'] = 'cancelled'
                    meta['message'] = '任务已被用户取消'
                    job.meta = meta
                    job.save()
                
                # Cancel the job
                job.cancel()
                return True
            
            return False
            
        except Exception as e:
            print(f"⚠️  Failed to cancel job {job_id}: {e}")
            return False

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get all jobs from the queue."""
        all_jobs = []

        if self._connected and self.queue and self.redis_conn:
            try:
                # 获取队列中的作业
                job_ids = self.queue.job_ids

                # 获取失败和完成的作业
                failed_jobs = self.queue.failed_job_registry.get_job_ids()
                finished_jobs = self.queue.finished_job_registry.get_job_ids()
                scheduled_jobs = self.queue.scheduled_job_registry.get_job_ids()

                all_job_ids = set(job_ids + failed_jobs + finished_jobs + scheduled_jobs)

                for job_id in all_job_ids:
                    try:
                        job = Job.fetch(job_id, connection=self.redis_conn)
                        if job:
                            meta = job.meta or {}
                            all_jobs.append({
                                "id": job.id,
                                "status": job.get_status(),
                                "meta": meta,
                                "created_at": job.created_at.isoformat() if job.created_at else None,
                                "enqueued_at": job.enqueued_at.isoformat() if job.enqueued_at else None,
                                "ended_at": job.ended_at.isoformat() if job.ended_at else None
                            })
                    except Exception:
                        continue
            except Exception as e:
                print(f"Error getting all jobs: {e}")

        return all_jobs

    def get_jobs_summary(self) -> Dict[str, int]:
        """Get summary of job counts by status."""
        summary = {
            "queued": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
            "scheduled": 0
        }

        if self._connected and self.queue:
            try:
                # 队列中的作业
                queued_jobs = self.queue.job_ids
                summary["queued"] = len(queued_jobs)

                # 失败的作业
                failed_jobs = self.queue.failed_job_registry.get_job_ids()
                summary["failed"] = len(failed_jobs)

                # 完成的作业
                finished_jobs = self.queue.finished_job_registry.get_job_ids()
                summary["completed"] = len(finished_jobs)

                # 调度的作业
                scheduled_jobs = self.queue.scheduled_job_registry.get_job_ids()
                summary["scheduled"] = len(scheduled_jobs)

                # 正在处理的作业
                workers = Worker.all(connection=self.redis_conn)
                summary["processing"] = len(workers)

            except Exception as e:
                print(f"Error getting job summary: {e}")

        return summary


# Global queue instance
_queue_instance: Optional[RedisQueue] = None


def get_queue() -> RedisQueue:
    """Get global queue instance."""
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = RedisQueue()
    return _queue_instance


def update_job_progress(progress: int, message: str, **kwargs):
    """
    Update job progress and message in Redis.
    
    This function should be called from within a RQ worker task.
    
    Args:
        progress: Progress percentage (0-100)
        message: Status message
        **kwargs: Additional metadata to store
    """
    if get_current_job is None:
        return
    job = get_current_job()
    if job:
        meta = job.meta or {}
        meta.update({
            "progress": progress,
            "message": message,
            **kwargs
        })
        job.meta = meta
        job.save()
