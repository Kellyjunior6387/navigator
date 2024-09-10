from flask import Flask
from groq import Groq
import os
import json
from flask import abort, jsonify, request
from typing import Dict
import requests


app = Flask(__name__)

#Function to send the message to llama
def get_response(message: str, system_content: str, temp: int = 2, token: int = 550,
                 stream: bool = False, response_format=None) -> str:
   
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY"),
    )

    chat_completion = client.chat.completions.create(
        messages=[
             {"role": "system", "content": system_content},
            {"role": "user","content": message,}
        ],
        model="llama3-groq-70b-8192-tool-use-preview",
        temperature=temp,
        max_tokens=token,
        stream=stream,
        response_format=response_format

    )

    return chat_completion.choices[0].message.content

def navigator():
    #Get the message from the request
    prompt = request.get_json()
    message = prompt.get('message')

    #Declare the routes in the uoncom app
    routes = {
    "home": "/",
    "blogs": "/blogs/page/1",
    "e-health": "/e-health",
    "e-games": "/e-games",
    "e-planners": "/e-planners",
    "uon-unsa": "/uon-unsa"
}
    #Define what the model should behave as
    system_content = 'You are a navigator that helps users go to different pages in my app. These are route pages in my app {}. Determine which page to navigate to based on the request message and return the route in json.If not route is matching the request strictly return None in the json'.format(routes)
    
    #Return the route if sucess otherwise nothing
    if message:
        response = get_response(message, system_content, 0.5, 150, False, {"type": "json_object"})
        parsed_response = json.loads(response)

        # Access the 'route' value
        route = parsed_response.get("route")

        if route:
            return jsonify({'intent': 'navigation'},
                       {'route': route},
                       {'message': 'Ok. Taking you there'}), 200
    return jsonify({'error': 'Bad request'}, 400)

def read_blog():
    data = request.get_json()

    # Error handling for missing 'message' in request
    message = data.get('message')
    if not message:
        return jsonify({"error": "No message provided"}), 400

    # Fetching blogs data
    try:
        response = requests.get('https://unsa-feng.uonbi.ac.ke/backend/php/uoncom/getBlogs.php')
        response.raise_for_status()  # Ensure the request was successful
        blogs = response.json()
    except requests.RequestException as e:
        return jsonify({"error": f"Failed to fetch blogs: {str(e)}"}), 500

    # Prepare blog descriptions for Groq
    blog_descriptions = [{"id": blog["blogID"], "title": blog["title"], "description": blog.get("description", "")} for blog in blogs]

    # Create a structured context for Groq
    blog_descriptions_str = "\n".join([f"ID: {bd['id']}, Title: {bd['title']}, Description: {bd['description']}" for bd in blog_descriptions])
    system_content = (
        f"You are a blog search assistant. Based on the user's description, find the matching blog description from the following list:\n\n"
        f"{blog_descriptions_str}\n\n"
        "Return the ID and title of the blog that best matches the user's description. Use only the provided data and do not reference external sources."
    )

    # Check if message exists, and call Groq API
    try:
        response = get_response(message, system_content)
        if response:
            return jsonify({
                'intent': 'reading',
                'message': response  # Ensure this is formatted correctly
            }), 200
        else:
            return jsonify({"error": "Failed to get response from Groq"}), 500
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/', methods=['POST'], strict_slashes=False)
def main():
    data = request.get_json()
    message = data.get("message")
    system_content = 'You are supposed to identify the intent of the user message.The intent can be either navigation or reading a blog.If the intent is other than that say you cannot do the task.Otherwise return a json object with the intent'
    response = get_response(message, system_content, 0.5, 400, False, {"type": "json_object"})
    parsed_response = json.loads(response)
    intent = parsed_response.get("intent")
    if intent == 'reading a blog':
        return read_blog()
    elif intent == 'navigation':
        return navigator()
    else:
        return jsonify({"message": 'I cannot manage to do that'}), 400

if __name__ == '__main__':
    app.run(debug=True)
