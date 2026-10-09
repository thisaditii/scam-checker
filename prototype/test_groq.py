from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()
llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
print(llm.invoke("Say hello in one line").content)