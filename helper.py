import google.generativeai as genai
from tidb_vector.integrations import TiDBVectorClient
from sentence_transformers import SentenceTransformer
from google.generativeai.types import HarmCategory, HarmBlockThreshold

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
        response = model.generate_content(prompt,
                                          safety_settings={
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    })
        return response.text

    class SimpleRetriever:
        def __init__(self, vector_store):
            self.vector_store = vector_store

        def retrieve(self, query_embedding, k=20):
            search_result = self.vector_store.query(query_embedding, k=k)
            return [
                {"text": r.document, "distance": r.distance}
                for r in search_result
            ]
    def rag_query(query, retriever):
        q = get_gemini_response(f"I need you to turn this question into a precise query that I can use to search a vector database of legal documents and constitution of India. The question is: {query}. Answer only with the query, and no headings. For example, if the question is 'What are my rights?', your response would be 'rights'. Another example, if the question is 'I was framed for murder, help me', your response would be 'frame, murder, rights of the accused, accusation, defense'.")
        print(f"Query: {q}")
        query_embedding = text_to_embedding(q)
        results = retriever.retrieve(query_embedding)
        response = get_gemini_response(f"You are a helpful lawyer who is adept in helping your clients get out of tricky situations. The client said: {query}. I queried my Indian Constitution database for {q} and these are the articles I got: {results}, now frame this into an answer in natural language and prepare the client robustly to fight his own case. Meticulously lay down the steps and articles that a lawyer would take and invoke in order to fight their own case. Elaborate each article and explain them properly so the client is fully prepared. Please do not include the original json in the answer. If my query: <{query}> is unrelated to anything about the Law, just answer by disregarding the database information and talking like a friendly lawyer person replying to '{query}'.")
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