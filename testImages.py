from fastapi import FastAPI, Form, File, UploadFile, Query
from typing import List, Optional
import base64
import aiohttp
import logging
import time
from fastapi.responses import JSONResponse

from config import OPENAI_API_KEY, OPENAI_ORG

app = FastAPI()
logger = logging.getLogger("uvicorn")

@app.post("/process-pet-image")
async def process_pet_images(
    pet_name: str = Form(...),
    petImages: List[UploadFile] = File(...),
    user_id: Optional[int] = Query(default=None)
):
    logger.debug(f'process_pet_images : {pet_name}')
    start_time = time.time()  # Start timing
    messages = [
        {"role": "system", "content": "petgpt_system_imagemessage"},
        {"role": "user", "content": [
            {"type": "text", 
             "text": f"It's {pet_name}'s photo. What's the pet type, breed, and age? 한국말로 답변해줘요. Return result as JSON like:\n"
                     "```json\n"
                     "{\n"
                     "  \"answer\": \"분류가 어렵습니다.\",\n"
                     "  \"name\": \"{pet_name}\",\n"
                     "  \"type\": \"dog\",\n"
                     "  \"breed\": \"믹스견\",\n"
                     "  \"age\": \"정확한 나이 추정 불가\"\n"
                     "}```"}
        ]}
    ]

    image_data = []
    for upload_file in petImages:
        contents = await upload_file.read()
        img_base64 = base64.b64encode(contents).decode("utf-8")
        if not img_base64.startswith('data:image'):
            img_base64 = f"data:image/jpeg;base64,{img_base64}"
        image_data.append(img_base64)
        upload_file.file.close()

        messages[1]["content"].append({
            "type": "image_url",
            "image_url": {"url": img_base64}
        })

    if user_id is not None:
        # Replace save_to_database with actual implementation
        pass

    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": "gpt-4o",  # Ensure this is the correct model
        "messages": messages,
        "max_tokens": 500
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status != 200:
                logger.error(f"Failed to get response from OpenAI API: {response.status}")
                return JSONResponse(status_code=response.status, content={"error": "Failed to process images"})
            
            result = await response.json()
            logger.debug(result)
            gpt4v = result['choices'][0]['message']['content']
            
            end_time = time.time()  # End timing
            processing_time = end_time - start_time
            formatted_time = f"{processing_time:.2f}s"
            response_data = {
                "message": gpt4v,
                "processing_time": formatted_time
            }
            if user_id is not None:
                response_data["user_id"] = user_id
            return response_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("testImages:app", host="0.0.0.0", port=9090, workers=21)
