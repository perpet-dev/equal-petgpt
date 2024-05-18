import httpx
import asyncio
import traceback

async def process_pet_images_async():
    url = "http://0.0.0.0:9090/process-pet-image"

    try:
        with open('/Users/ivanpro/Dropbox/Equal/img/gr.jpeg', 'rb') as file1, \
             open('/Users/ivanpro/Dropbox/Equal/img/nc.jpg', 'rb') as file2:

            files = [
                ('petImages', ('gr.jpeg', file1, 'image/jpeg')),
                ('petImages', ('nc.jpg', file2, 'image/jpeg'))
            ]

            data = {
                'pet_name': 'Buddy',
            }

            timeout = httpx.Timeout(60.0, read=60.0)  # Increase timeout to 60 seconds
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, data=data, files=files)
                print("Status:", response.status_code)
                print("Response:", response.json())
    except Exception as e:
        print(f"Exception in process_pet_images_async: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(process_pet_images_async())
