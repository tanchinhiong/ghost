import os
import sys
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv, find_dotenv
from langchain.memory import ConversationBufferMemory
from langchain.agents import initialize_agent, AgentType
from tools import get_tools
from langchain.chat_models import AzureChatOpenAI, ChatVertexAI, ChatOpenAI
from langchain.llms import OpenAI, AzureOpenAI, VertexAI
from waitress import serve
import webbrowser
from datetime import datetime

from config import specs_file, output_file, retries, provider
from config import provider_config as cfg

# Initialize
llm = None

# get path for static files
static_dir = os.path.join(os.path.dirname(__file__), 'static')  
if not os.path.exists(static_dir): 
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

# initialise the agent
def initAgent():
    global llm
    print("\033[96mInitialising Ghost with the following specifications:\033[0m")
    # read the specifications from file
    specs = ""
    with open(specs_file, 'r') as file:
        specs = file.read()
    print(specs, "\nlength:", len(specs), "words")
    print(f"\033[96mUsing {cfg.provider} \033[0m")

    # OpenAI
    if cfg.provider == "openai":
        if cfg.model_name.startswith("gpt-4") or cfg.model_name.startswith("gpt-3.5"):
            llm = ChatOpenAI(
                temperature=0.7,
                model_name=cfg.model_name,
                openai_api_key=cfg.api_key,
                max_retries=retries,
            )      
        else:
            llm = OpenAI(
                temperature=0.7,
                model_name=cfg.model_name,
                openai_api_key=cfg.api_key,
                max_retries=retries,
            )      


    # Azure OpenA
    if cfg.provider == "azure":
        if cfg.model_name.startswith("gpt-4") or cfg.model_name.startswith("gpt-3.5"):                       
            llm = AzureChatOpenAI(
                temperature=0.7,
                openai_api_base=cfg.base_url,
                openai_api_version=cfg.api_version,
                model_name=cfg.model_name,
                deployment_name=cfg.deployment_name,
                openai_api_key=cfg.api_key,
                max_retries=retries,
                openai_api_type = "azure",
            )   
        else:
            llm = AzureOpenAI(
                temperature=0.7,
                openai_api_base=cfg.base_url,
                openai_api_version=cfg.api_version,
                model_name=cfg.model_name,
                deployment_name=cfg.deployment_name,
                openai_api_key=cfg.api_key,
                max_retries=retries,
                openai_api_type = "azure",
            )   

    # Google Vertex AI (PaLM)
    if cfg.provider == "palm":
        if cfg.model_name == "chat-bison" or cfg.odel_name == "codechat-bison":
            llm = ChatVertexAI(
                temperature=0.7,
                model_name=cfg.model_name,
                location=cfg.location,
                max_output_tokens=1024,
            )
        else:
            llm = VertexAI(
                temperature=0.7,
                model_name=cfg.model_name,
                location=cfg.location,
                max_output_tokens=1024,
            )

    if llm == None:
        sys.exit("No valid LLM configured:" + provider)  

    print(f"\033[96mWith {llm.model_name}\033[0m") 


    FORMAT_INSTRUCTIONS = """Do not put any quotes in output response and To use a tool, please use the following format:

\```
Thought: Do I need to use a tool? Yes
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
\```

When you have a response to say to the Human, or if you do not need to use a tool, you MUST use the following format(the prefix of "Thought: " and "{ai_prefix}: " are must be included):

\```
Thought: Do I need to use a tool? No
{ai_prefix}: [your response here]
\```
do not create any triplet quotes single or double in the output,only create ASCII characters in output and no comments required
"""

    # initialise agent execut
    agent = initialize_agent(
        get_tools(), 
        llm, 
        agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,         
        memory=ConversationBufferMemory(memory_key="chat_history", return_messages=True),
        agent_kwargs={"format_instructions": FORMAT_INSTRUCTIONS},
        handle_parsing_errors="Check the output and correct it to make it conform.",
        verbose=True)

    agent.run(specs)
    return agent

def save(prompt, response):
     with open(output_file, 'a') as file:
         file.write("# " + provider.upper() + " " + llm.model_name.upper() + 
                    " <small>[" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "]</small>" + 
                    "\n## PROMPT\n" + prompt +
                    "\n## RESPONSE\n" + response + 
                    "\n\n")

# start server
print("\033[96mStarting Ghost at http://127.0.0.1:1337\033[0m")
ghost = Flask(__name__, static_folder=static_dir, template_folder=static_dir)
agent = initAgent()

# server landing page
@ghost.route('/')
def landing():
    return render_template('index.html')

# run
@ghost.route('/run', methods=['POST'])
def run():
    data = request.json
    response = agent.run(data['input'])   
    save(data['input'], response) 
    return jsonify({'input': data['input'],
                    'response': response})

if __name__ == '__main__':
    print("\033[93mGhost started. Press CTRL+C to quit.\033[0m")
    # webbrowser.open("http://127.0.0.1:1337")
    # serve(ghost, host='127.0.0.1', port=1337)
    serve(ghost, port=1337)

