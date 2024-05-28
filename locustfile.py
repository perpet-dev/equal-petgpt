from locust import HttpUser, TaskSet, task, between, events
import httpx
import asyncio
import traceback
import random
import time
from contextlib import closing

class UserBehavior(TaskSet):

    @task
    def process_pet_images(self):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            loop.create_task(self.process_pet_images_async())
        else:
            loop.run_until_complete(self.process_pet_images_async())

    async def process_pet_images_async(self):
        url = f"{self.user.host}/process-pet-image"
        start_time = time.time()

        try:
            with open('/Users/ivanpro/Dropbox/Equal/img/nc.jpg', 'rb') as file1:
                with closing(file1) as f1:
                    files = [
                        ('petImages', ('nc.jpg', f1, 'image/jpeg'))
                    ]

                    data = {
                        'pet_name': 'Buddy',
                        'user_id': 204 #random.randint(1, 1000)  # Simulate different user IDs
                    }

                    print("Data:", data)

                    timeout = httpx.Timeout(10.0, read=10.0)  # Increase timeout to 30 seconds
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        response = await client.post(url, data=data, files=files)
                        response.raise_for_status()
                        elapsed_time = time.time() - start_time
                        self.user.environment.events.request.fire(
                            request_type="POST",
                            name="/process-pet-image",
                            response_time=elapsed_time * 1000,  # Convert to milliseconds
                            response_length=len(response.content),
                            exception=None  # Indicate success
                        )
                        print("Status:", response.status_code)
                        print("Response:", response.json())
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.user.environment.events.request.fire(
                request_type="POST",
                name="/process-pet-image",
                response_time=elapsed_time * 1000,  # Convert to milliseconds
                response_length=0,
                exception=e  # Indicate failure
            )
            print(f"Exception in process_pet_images_async: {e}")
            traceback.print_exc()

class WebsiteUser(HttpUser):
    tasks = [UserBehavior]
    wait_time = between(1, 5)
    host = "https://api2.equal.pet/petgpt-service"

if __name__ == "__main__":
    import os
    os.system("locust -f locustfile.py --host=https://api2.equal.pet/petgpt-service --users 10 --spawn-rate 5")
