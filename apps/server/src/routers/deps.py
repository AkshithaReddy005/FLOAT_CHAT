# Shared application-level singletons
# These are set once during app startup by main.py

from rag_pipeline.vector_store import VectorStore
from chat_bot.chatbot_service import ChatbotService
from utils.example_query_generator import ExampleQueryGenerator
from database.two_phase_coordinator import TwoPhaseCoordinator

vector_store: VectorStore = None
chatbot_service: ChatbotService = None
example_generator: ExampleQueryGenerator = None
transaction_coordinator: TwoPhaseCoordinator = None

def initialize():
    global vector_store, chatbot_service, example_generator, transaction_coordinator
    vector_store = VectorStore()
    chatbot_service = ChatbotService(vector_store)
    example_generator = ExampleQueryGenerator(vector_store)
    transaction_coordinator = TwoPhaseCoordinator(chunk_size=100)
