import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import CohereEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.llms import Cohere
from dotenv import load_dotenv

load_dotenv()


def get_vectorstore_from_url(url):
    loader = WebBaseLoader(url)
    documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter()
    document_chunks = text_splitter.split_documents(documents=documents)
    vector_store = Chroma.from_documents(document_chunks, CohereEmbeddings())
    # print(vector_store)
    return vector_store

def get_context_retriever_chain(vector_store):
    llm_model = Cohere()
    retriever = vector_store.as_retriever()
    prompt = ChatPromptTemplate.from_messages([
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}"),
        ("user", "Given the above conversation, generate a search query to look up in order to get information relevant to the entire conversation")
    ])
    retriever_chain = create_history_aware_retriever(llm_model, retriever, prompt)
    return retriever_chain


def get_conversational_rag_chain(retriever_chain):
    llm_model = Cohere()
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Answer the user's questions based on the below context:\n\n{context}"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}"),
    ])
    stuff_document_chain = create_stuff_documents_chain(llm_model, prompt)

    return create_retrieval_chain(retriever_chain, stuff_document_chain)


def get_response(user_input):
    retriever_chain = get_context_retriever_chain(st.session_state.vector_store)

    conversation_rag_chain = get_conversational_rag_chain(retriever_chain)

    response = conversation_rag_chain.invoke({
            "chat_history": st.session_state.chat_history,
            "input": user_query
        })
    
    return response['answer']


st.set_page_config(page_title="Scrape the Web", layout="wide")

st.title("Chat with websites")


with st.sidebar:
    st.header("Settings")
    website_url = st.text_input("Website URL")

if website_url is None or website_url=="":
    st.info("Please enter a website URL")
else:
    #session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
        AIMessage(content="Hello, this is AVA, your AI powered bot. How may I help you?"),
        ]
    
    if "vector_store" not in st.session_state:
        st.session_state.vector_store = get_vectorstore_from_url(website_url)

    # create conversation chain
    
    # retriever_chain = get_context_retriever_chain(st.session_state.vector_store)

    # conversation_rag_chain = get_conversational_rag_chain(retriever_chain)


    user_query = st.chat_input("Type your message here...")

    if user_query is not None and user_query!="":
        # response = conversation_rag_chain.invoke({
        #     "chat_history": st.session_state.chat_history,
        #     "input": user_query
        # })

        response = get_response(user_query)
        # st.write(response)
        st.session_state.chat_history.append(HumanMessage(content=user_query))
        st.session_state.chat_history.append(AIMessage(content=response))

    # with st.sidebar:
    #     st.write(st.session_state.chat_history)

    for message in  st.session_state.chat_history:
        if isinstance(message, AIMessage):
            with st.chat_message("AI"):
                st.write(message.content)
        elif isinstance(message, HumanMessage):
            with st.chat_message("Human"):
                st.write(message.content)
