"""
Queue Manager for CC Killer Bot
Handles high-concurrency CC checking with priority processing.
VIP > Paid > Free users
"""

import asyncio
from dataclasses import dataclass, field
from typing import Callable, Any, Optional
from datetime import datetime

# Priority levels (lower = higher priority)
PRIORITY_VIP = 0
PRIORITY_PAID = 1
PRIORITY_FREE = 2

# Configuration
MAX_WORKERS = 50  # Concurrent checks
MAX_QUEUE_SIZE = 10000  # Maximum items in queue

@dataclass(order=True)
class QueueItem:
    priority: int
    timestamp: float = field(compare=False)
    user_id: int = field(compare=False)
    card: str = field(compare=False)
    gate: str = field(compare=False)
    callback: Callable = field(compare=False)
    message: Any = field(compare=False)
    client: Any = field(compare=False)

class CCQueue:
    def __init__(self):
        self.queue = asyncio.PriorityQueue(maxsize=MAX_QUEUE_SIZE)
        self.workers_running = False
        self.active_checks = 0
        self.total_processed = 0
        self.user_positions = {}  # Track queue positions per user
        
    async def add_to_queue(self, user_id: int, card: str, gate: str, 
                           callback: Callable, message: Any, client: Any,
                           is_vip: bool = False, plan: str = "FREE"):
        """Add a CC check to the queue with priority based on plan."""
        
        # Determine priority
        if is_vip or plan == "VIP":
            priority = PRIORITY_VIP
        elif plan in ["ULTIMATE", "STANDARD", "BASIC"]:
            priority = PRIORITY_PAID
        else:
            priority = PRIORITY_FREE
            
        item = QueueItem(
            priority=priority,
            timestamp=datetime.now().timestamp(),
            user_id=user_id,
            card=card,
            gate=gate,
            callback=callback,
            message=message,
            client=client
        )
        
        try:
            self.queue.put_nowait(item)
            # Track user's items in queue
            if user_id not in self.user_positions:
                self.user_positions[user_id] = 0
            self.user_positions[user_id] += 1
            return True
        except asyncio.QueueFull:
            return False
    
    def get_queue_size(self) -> int:
        return self.queue.qsize()
    
    def get_user_pending(self, user_id: int) -> int:
        return self.user_positions.get(user_id, 0)
    
    def get_stats(self) -> dict:
        return {
            "queue_size": self.queue.qsize(),
            "active_workers": self.active_checks,
            "total_processed": self.total_processed,
            "max_workers": MAX_WORKERS
        }
    
    async def worker(self, worker_id: int):
        """Worker that processes queue items."""
        while self.workers_running:
            try:
                # Wait for an item with timeout
                item = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                self.active_checks += 1
                
                try:
                    # Call the gate check function
                    await item.callback(
                        item.client, 
                        item.message, 
                        item.card, 
                        item.gate
                    )
                    self.total_processed += 1
                except Exception as e:
                    print(f"[Worker {worker_id}] Error: {e}")
                finally:
                    self.active_checks -= 1
                    # Decrement user's pending count
                    if item.user_id in self.user_positions:
                        self.user_positions[item.user_id] -= 1
                        if self.user_positions[item.user_id] <= 0:
                            del self.user_positions[item.user_id]
                    self.queue.task_done()
                    
            except asyncio.TimeoutError:
                continue  # No items, keep waiting
            except Exception as e:
                print(f"[Worker {worker_id}] Fatal: {e}")
                await asyncio.sleep(1)
    
    async def start_workers(self):
        """Start the worker pool."""
        if self.workers_running:
            return
            
        self.workers_running = True
        print(f"🚀 Starting {MAX_WORKERS} queue workers...")
        
        # Create worker tasks
        for i in range(MAX_WORKERS):
            asyncio.create_task(self.worker(i))
        
        print("✅ Queue workers started!")
    
    async def stop_workers(self):
        """Stop all workers gracefully."""
        self.workers_running = False
        # Wait for queue to empty
        await self.queue.join()
        print("🛑 Queue workers stopped.")

# Global queue instance
cc_queue = CCQueue()

async def init_queue():
    """Initialize and start the queue system."""
    await cc_queue.start_workers()
    
def get_queue() -> CCQueue:
    """Get the global queue instance."""
    return cc_queue
