import requests
from langchain import OpenAI
from langchain import PromptTemplate
from flask import Flask, render_template, jsonify
from flask_cors import CORS
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.docstore.document import Document



app = Flask(__name__)
CORS(app)


template = """
title: {title}
description: {desc}
the output should be in the format that is provided below:
'''
    Title: (title of the card)
    Decision: (choose one of the following depending on how many points in the positive points to the negative points (Good/Bad/Buy/Don't buy)
    Summary: (write a short version of the description provided)
    Why to buy:
    1-
    2-
    3-
    n-
    
    Why not to buy:
    1-
    2-
    3-
    n-
    
'''
"""

prompt = PromptTemplate(
    input_variables=["title", "desc"],
    template=template,
)

llm = OpenAI(temperature=0, model_name="gpt-3.5-turbo")

# Trello API credentials
API_KEY = '00e260a6242a488071b11c43f7d5f7d5'
TOKEN = 'ATTAce95851b591950024ce8e4b63e83270a7f1b2d47184aacdf378dc63ebda5d85e0848598D'

# URL for adding a comment to a card
COMMENT_URL = 'https://api.trello.com/1/cards/{}/actions/comments?key={}&token={}'

# Function to process the card data using Python code
def process_card_data(desc, title):
    processed_data = llm(prompt.format(title=title, desc=desc))
    return processed_data

#split the desc
def split_document(document):
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    documents = text_splitter.split_documents(document)
    return documents

#create vector database
def vector_store(documents):
    embeddings = OpenAIEmbeddings()
    vecstore = Chroma.from_documents(documents, embeddings)
    return vecstore

# Function to add a comment to the card with the output
def add_comment_to_card(card_id, comment):
    comment_url = COMMENT_URL.format(card_id, API_KEY, TOKEN)
    payload = {'text': comment}
    requests.post(comment_url, json=payload)

# Retrieve the card details using the Trello API
def retrieve_card_details(card_id):
    card_url = f'https://api.trello.com/1/cards/{card_id}?key={API_KEY}&token={TOKEN}'
    response = requests.get(card_url)
    card_data = response.json()
    return card_data

#create qa
def qa_retrieval(vectorstore):
    qa = RetrievalQA.from_chain_type(
        llm=OpenAI(temperature=0,model_name="gpt-3.5-turbo"), 
        chain_type="stuff", 
        retriever=vectorstore.as_retriever(),
    )
    return qa


@app.route('/query/<vecstore>/<input>', methods=['GET'])
def query(vecstore,input):
    vecstore = vecstore
    qa = qa_retrieval(vectorstore=vecstore)
    output = qa.run(input)
    return output

@app.route('/process_card/<card_id>', methods=['GET'])
def process_card_and_add_comment(card_id):
    try:
        card_data = retrieve_card_details(card_id)

        # Extract the card description
        card_desc = card_data['desc']
        card_title = card_data['name']

        # Process the card data using Python code
        output = process_card_data(card_desc, card_title)

        # Add a comment with the output to the card
        add_comment_to_card(card_id, output)

        return jsonify('Card processed successfully')
    except Exception as e:
        print(e)
        return jsonify('Error processing card')

@app.route('/', methods=['GET'])
def MainAccess():
    response_data = {"message": "احلى مسا على اخويا اشرف و اخويا عمرو و حنفي"}
    return jsonify(response_data)

@app.route('/powerUpScript', methods=['GET'])
def powerUpScript():
    return render_template('index.html')

@app.route('/modal/<card_id>', methods=['GET'])
def modal(card_id):
    cardid=card_id
    
    card_data = retrieve_card_details(card_id)

    # Extract the card description
    card_desc = card_data['desc']
    
    doc = Document(page_content=card_desc)
    text=[doc]
    
    splittedDocuments = split_document(document=text)

    vectorstore = vector_store(documents=splittedDocuments)

    
    return render_template('modal.html',vecstore=vectorstore)

if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))
