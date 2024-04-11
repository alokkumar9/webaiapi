import asyncio
from typing import AsyncIterable
import os
import requests
import json
import random
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
from pydantic import BaseModel
from fastapi import Response
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from langchain_openai import ChatOpenAI

os.environ["OPENAI_API_KEY"]='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'

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    website_type: str
    content_type: str=["about", "services"]
    expert_in: str="website content creation"
    length:int=50

def human_template_modifier(content_type, length, website_type):
    human_template="Create content for {content_type} section of {length} words for a {website_type} website"
    return human_template

async def send_message(message: Message) -> AsyncIterable[str]:
    callback = AsyncIteratorCallbackHandler()
    model = ChatOpenAI(
        streaming=True,
        verbose=True,
        callbacks=[callback],
        temperature=0.9
    )

    template = "You are expert in {expert_in}."
    system_message_prompt = SystemMessagePromptTemplate.from_template(template)
    # human_template = human_template_modifier(message.content_type,message.length,message.website_type)
    human_template="Create content for {content_type} section of {length} words for a {website_type} website"
    human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)
    chat_prompt = ChatPromptTemplate.from_messages(
        [system_message_prompt, human_message_prompt]
    )
    complete_prompt = chat_prompt.format_prompt(
        expert_in=message.expert_in,
        content_type=message.content_type,
        length=message.length,
        website_type=message.website_type
    ).to_messages()

    task = asyncio.create_task(
        model.agenerate(messages=[complete_prompt])
    )

    try:
        async for token in callback.aiter():
            yield token
    except Exception as e:
        print(f"Caught exception: {e}")
    finally:
        callback.done.set()
    await task

@app.post("/text_content")
async def stream_text(message: Message):
    generator = send_message(message)
    # return StreamingResponse(generator, media_type="text/event-stream")
    return StreamingResponse(generator, media_type="application/x-ndjson")

# @app.get("/image/")
# async def get_image(image_name:str, orientation: str="landscape", size: str="original", per_page:int=1):

#     # image_name="red flowers"
#     # orientation="landscape"
#     # per_page=3
#     # size="small"
#     page_no=random.randint(1,10)
    
#     pexel_api="KYA5omO4oxYPmua1IRniIB1iDZiAJmubzQ5xHOT3w770K330iHkXUM19"
#     # https://api.pexels.com/v1/search?query=red car&orientation=landscape&per_page=1&size=small&page=page_no
#     # keyword="red car"
#     url=f"https://api.pexels.com/v1/search?query={image_name}&orientation={orientation}&per_page={per_page}&size={size}&page={page_no}"
#     headers = {
#         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
#         "Authorization": "KYA5omO4oxYPmua1IRniIB1iDZiAJmubzQ5xHOT3w770K330iHkXUM19"
#     }

#     # headers = {"User-Agent": user_agent}
#     response = requests.get(url, headers=headers)
#     byte_response_content=response.content
#     json_data = json.loads(byte_response_content.decode('utf-8'))

#     photos=json_data["photos"]
#     if size=="original":
#         required_photos=[photo["src"][orientation] for photo in photos]
#     else:
#         required_photos=[photo["src"][size] for photo in photos]

#     return json.dumps(required_photos)

#     # https://api.pexels.com/v1/search?query=car&orientation=landscape"
#     # if message.islandscape:
#     # orientation=""
#     # headers = {"Content-type": "application/json"}
#     # with requests.post(url, json=data, headers=headers)


def get_pexels_images(image_name: str, orientation: str = "landscape", size: str = "original", per_page: int =1):
    """
    Retrieves images from Pexels API based on search parameters.

    Args:
        image_name (str): The search query for images (e.g., "red flowers").
        orientation (str, optional): Image orientation ("landscape" or "portrait"). Defaults to "landscape".
        size (str, optional): Image size ("original" or "small"). Defaults to "original".
        per_page (int, optional): Number of images per page. Defaults to 1.

    Returns:
        list: List of image URLs.
    """
    page_no = random.randint(1, 10)
    pexel_api = "KYA5omO4oxYPmua1IRniIB1iDZiAJmubzQ5xHOT3w770K330iHkXUM19"
    url = f"https://api.pexels.com/v1/search?query={image_name}&orientation={orientation}&per_page={per_page}&size={size}&page={page_no}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
        "Authorization": pexel_api,
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception if the response status code is not 200
        json_data = response.json()
        photos = json_data.get("photos", [])
        if size == "original":
            required_photos = [photo["src"].get(orientation) for photo in photos]
        else:
            required_photos = [photo["src"].get(size) for photo in photos]
        return required_photos
    except requests.RequestException as e:
        print(f"Error fetching images: {e}")
        return []

@app.get("/image/")
async def get_image(image_name: str, orientation: str = "landscape", size: str = "original", per_page: int = 1):
    image_urls = get_pexels_images(image_name, orientation, size, per_page)
    data = {"image_url": image_urls}
    return data


db_config = {
    'dbname': 'postgres',
    'user': 'postgres',
    'password': 'admin',
    'host': 'localhost',
    'port': '5432'
}

# Establish a connection to the PostgreSQL database
import psycopg2
def connect():
    try:
        conn = psycopg2.connect(**db_config)
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {str(e)}")
        return None
# def home():
#     return jsonify({"status": "Home address", "code": 1})

@app.post("/database")
async def get_database(unique_id: str, content_part:str=''):
    connection = connect()
    if connection:
        # return jsonify({"status": "successfully connected", "code": 1})
        try:
            with connection.cursor() as cursor:
                # Execute a SELECT query to retrieve all rows from the table
                if content_part=='':
                    cursor.execute(f"SELECT * FROM test WHERE unique_id={unique_id}")
                    rows = cursor.fetchall()
                else:
                    cursor.execute(f"SELECT {content_part} FROM test WHERE unique_id={unique_id}")
                    rows = cursor.fetchall()
                # print(rows)
                # Process the retrieved rows (e.g., print them)
                for row in rows:
                    print(row)
                # return jsonify({"status": "Content fetched", "code": 2})
                return row

        except Exception as e:
            print(f"Error executing query: {str(e)}")

        finally:
            pass
            # Close the connection
            # connection.close()

    else:
        test='{"status": "Failed to connect", "code": 0}'
        # return jsonify({"status": "Failed to connect", "code": 0})
        return Response(content=test, media_type="application/json")

        
    