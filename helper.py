import google.generativeai as genai
import os
from tidb_vector.integrations import TiDBVectorClient
from sentence_transformers import SentenceTransformer

def gen(query):
    embed_model = SentenceTransformer("sentence-transformers/msmarco-MiniLM-L12-cos-v5", trust_remote_code=True)
    embed_model_dims = embed_model.get_sentence_embedding_dimension()

    def text_to_embedding(text):
        """Generates vector embeddings for the given text."""
        embedding = embed_model.encode(text)
        return embedding.tolist()
    
    capath = 'isrgrootx1.pem'

    vector_store = TiDBVectorClient(
    table_name='const',
    connection_string=f'mysql+mysqldb://2zU6uAawmvKDo4B.root:YHOr6v6CPfCNK3WI@gateway01.eu-central-1.prod.aws.tidbcloud.com:4000/test?ssl_ca={capath}',
    vector_dimension=embed_model_dims,
    drop_existing_table=False
    )

    GOOGLE_API_KEY="AIzaSyDdwSHEaQfEkeIXd8h2T4uIPaG4M6kZijk"
    genai.configure(api_key=GOOGLE_API_KEY)

    def get_gemini_response(prompt):
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            
            if response.candidates:
                # Check if there's any blocked content
                if response.prompt_feedback.block_reason:
                    print(f"Response blocked. Reason: {response.prompt_feedback.block_reason}")
                    return "I'm sorry, but I couldn't generate a response to that query due to content safety concerns."
                
                # If not blocked, return the response text
                return response.text
            else:
                # Check safety ratings
                safety_ratings = response.prompt_feedback.safety_ratings
                print(f"No response generated. Safety ratings: {safety_ratings}")
                return "I'm sorry, but I couldn't generate a response to that query."
        except Exception as e:
            print(f"An error occurred while generating response: {str(e)}")
            return "An error occurred while processing your request."

    class SimpleRetriever:
        def __init__(self, vector_store):
            self.vector_store = vector_store

        def retrieve(self, query_embedding, k=10):
            search_result = self.vector_store.query(query_embedding, k=k)
            return [
                {"text": r.document, "distance": r.distance}
                for r in search_result
            ]

    def rag_query(query, retriever):
        query_embedding = text_to_embedding(query)
        results = retriever.retrieve(query_embedding)
        response = get_gemini_response(f"You are a helpful lawyer who is adept in helping your clients get out of tricky situations. I queried my constitution database for {query} and this is the information I got: {results}, now frame this into an answer in natural language. Please do not include the original json in the answer. If my query: <{query}> is unrelated to anything about the Law, just answer by disregarding the database information and talking like a normal person replying to <{query}>.")
        return response

    def generate(query):
        try:
            retriever = SimpleRetriever(vector_store)
            if "Content of " in query:
                # Split the query to separate PDF contents and user question
                parts = query.split("User Question:")
                pdf_contents = parts[0]
                user_question = parts[1] if len(parts) > 1 else ""
                response = get_gemini_response(f"""You are a helpful lawyer who is adept in helping your clients get out of tricky situations. 
                I have the following PDF contents: 
                {pdf_contents.strip()} 
                The user asked: {user_question.strip()}. 
                Please provide an answer based on this information. If the question is related to the PDF contents, use that information in your response. 
                If the question is unrelated to the PDF contents or law, just answer as a normal person would.""")
            else:
                response = rag_query(query, retriever)
            return response
        except Exception as e:
            print(f"An error occurred in generate function: {str(e)}")
            return "An error occurred while processing your request."
    
    return generate(query)

if __name__ == "__main__":
    query = "What are my rights?"
    response = gen(query)
    print(response)