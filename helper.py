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
    
    capath = '/etc/ssl/certs/ca-certificates.crt'

    vector_store = TiDBVectorClient(
    table_name='const',
    connection_string=f'mysql+mysqldb://2zU6uAawmvKDo4B.root:YHOr6v6CPfCNK3WI@gateway01.eu-central-1.prod.aws.tidbcloud.com:4000/test?ssl_ca={capath}',
    vector_dimension=embed_model_dims,
    drop_existing_table=False
    )

    GOOGLE_API_KEY="AIzaSyDdwSHEaQfEkeIXd8h2T4uIPaG4M6kZijk"
    genai.configure(api_key=GOOGLE_API_KEY)

    def get_gemini_response(prompt):
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text

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
        retriever = SimpleRetriever(vector_store)
        response = rag_query(query, retriever)
        return response
    
    return generate(query)


if __name__ == "__main__":
    query = "What are my rights?"
    response = gen(query)
    print(response)