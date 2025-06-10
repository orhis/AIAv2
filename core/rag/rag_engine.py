# core/rag/rag_engine.py
import sys
import os
sys.path.append(os.path.dirname(__file__))
from typing import List, Dict, Any, Optional
from recipe_loader import RecipeLoader

# Sprawdź dostępność LangChain
try:
    from langchain.schema import Document
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS
    from langchain_huggingface import HuggingFaceEmbeddings
    LANGCHAIN_AVAILABLE = True
except ImportError:
    print("⚠️ LangChain nie jest zainstalowany. Używam prostego wyszukiwania.")
    LANGCHAIN_AVAILABLE = False

class SimpleRAGEngine:
    """Prosty silnik RAG bez LangChain (fallback)"""
    
    def __init__(self):
        self.loader = RecipeLoader()
        self.recipes = []
        self.skladniki = {}
    
    def initialize(self):
        """Inicjalizacja danych"""
        self.recipes = self.loader.load_recipes()
        self.skladniki = self.loader.load_skladniki()
        return len(self.recipes) > 0
    
    def find_recipes_by_ingredients(self, user_ingredients: List[str], category: str = None) -> List[Dict]:
        """Znajdź przepisy na podstawie składników użytkownika"""
        matching_recipes = []
        
        for recipe in self.recipes:
            # Filtruj po kategorii jeśli podana
            if category and recipe.get('category') != category:
                continue
            
            recipe_ingredients = self.loader.parse_ingredients(recipe['ingredients'])
            
            # Sprawdź ile składników się pokrywa
            matches = 0
            for user_ing in user_ingredients:
                if any(user_ing.lower() in recipe_ing.lower() or recipe_ing.lower() in user_ing.lower() 
                       for recipe_ing in recipe_ingredients):
                    matches += 1
            
            if matches > 0:
                recipe_copy = recipe.copy()
                recipe_copy['match_score'] = matches
                recipe_copy['match_percentage'] = round((matches / len(recipe_ingredients)) * 100, 1)
                matching_recipes.append(recipe_copy)
        
        # Sortuj po wyniku dopasowania
        matching_recipes.sort(key=lambda x: x['match_score'], reverse=True)
        return matching_recipes

class LangChainRAGEngine:
    """Zaawansowany silnik RAG z LangChain"""
    
    def __init__(self):
        self.loader = RecipeLoader()
        self.recipes = []
        self.skladniki = {}
        self.vectorstore = None
        self.embeddings = None
    
    def initialize(self):
        """Inicjalizacja z embeddings"""
        try:
            print("🔄 Inicjalizacja RAG z LangChain...")
            
            # Wczytaj dane
            self.recipes = self.loader.load_recipes()
            self.skladniki = self.loader.load_skladniki()
            
            if not self.recipes:
                return False
            
            # Stwórz embeddings (uniwersalny model)
            print("📥 Ładowanie modelu embeddings...")
            self.embeddings = HuggingFaceEmbeddings(
                model_name="all-MiniLM-L6-v2",  # Szybki i uniwersalny model
                model_kwargs={'device': 'cpu'}
            )
            
            # Przygotuj dokumenty
            documents = self._prepare_documents()
            
            # Stwórz vector store
            print("🔍 Tworzenie vector store...")
            self.vectorstore = FAISS.from_documents(documents, self.embeddings)
            
            print("✅ RAG zainicjalizowany pomyślnie!")
            return True
            
        except Exception as e:
            print(f"❌ Błąd inicjalizacji RAG: {e}")
            return False
    
    def _prepare_documents(self) -> List[Document]:
        """Przygotuj dokumenty dla vector store"""
        documents = []
        
        for recipe in self.recipes:
            # Stwórz tekst dokumentu
            content = f"Przepis: {recipe['title']}. "
            content += f"Składniki: {recipe['ingredients']}. "
            content += f"Kategoria: {recipe['category']}."
            
            # Metadata
            metadata = {
                'title': recipe['title'],
                'category': recipe['category'],
                'ingredients': recipe['ingredients']
            }
            
            documents.append(Document(page_content=content, metadata=metadata))
        
        return documents
    
    def find_recipes_by_ingredients(self, user_ingredients: List[str], category: str = None, k: int = 5) -> List[Dict]:
        """Znajdź przepisy używając vector search"""
        if not self.vectorstore:
            print("❌ Vector store nie jest zainicjalizowany")
            return []
        
        try:
            # Stwórz query
            query = f"Składniki: {', '.join(user_ingredients)}"
            if category:
                query += f" kategoria: {category}"
            
            # Wyszukaj podobne dokumenty
            docs = self.vectorstore.similarity_search(query, k=k*2)  # Pobierz więcej na start
            
            results = []
            for doc in docs:
                recipe_data = {
                    'title': doc.metadata['title'],
                    'ingredients': doc.metadata['ingredients'], 
                    'category': doc.metadata['category'],
                    'similarity_score': 0.8  # Placeholder
                }
                
                # Filtruj po kategorii jeśli podana
                if category and recipe_data['category'] != category:
                    continue
                
                results.append(recipe_data)
                
                if len(results) >= k:
                    break
            
            return results
            
        except Exception as e:
            print(f"❌ Błąd wyszukiwania: {e}")
            return []

class RecipeRAG:
    """Główna klasa RAG - automatycznie wybiera dostępny engine"""
    
    def __init__(self, use_langchain: bool = True):
        self.use_langchain = use_langchain and LANGCHAIN_AVAILABLE
        
        if self.use_langchain:
            print("🚀 Używam LangChain RAG Engine")
            self.engine = LangChainRAGEngine()
        else:
            print("🔧 Używam Simple RAG Engine")
            self.engine = SimpleRAGEngine()
    
    def initialize(self) -> bool:
        """Inicjalizacja RAG"""
        return self.engine.initialize()
    
    def suggest_recipes(self, user_ingredients: List[str], category: str = None, max_results: int = 5) -> Dict[str, Any]:
        """Główna funkcja - sugeruj przepisy na podstawie składników"""
        
        if not user_ingredients:
            return {"error": "Brak składników do wyszukiwania"}
        
        print(f"🔍 Szukam przepisów dla: {user_ingredients}")
        if category:
            print(f"📂 Kategoria: {category}")
        
        # Znajdź przepisy
        recipes = self.engine.find_recipes_by_ingredients(
            user_ingredients, 
            category=category
        )
        
        if not recipes:
            return {
                "message": "Nie znaleziono przepisów z podanymi składnikami",
                "suggestions": ["Spróbuj innych składników", "Sprawdź dostępne kategorie"]
            }
        
        # Ogranicz wyniki
        recipes = recipes[:max_results]
        
        # Grupuj po kategoriach
        by_category = {}
        for recipe in recipes:
            cat = recipe['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(recipe)
        
        return {
            "found_recipes": len(recipes),
            "by_category": by_category,
            "all_recipes": recipes
        }

# === Test lokalny ===
if __name__ == "__main__":
    print("🧪 Test RAG Engine")
    
    # Inicjalizacja
    rag = RecipeRAG()
    
    if rag.initialize():
        print("\n🔍 Test 1: Składniki podstawowe")
        result = rag.suggest_recipes(['jajka', 'papryka'])
        print(f"Znaleziono: {result.get('found_recipes', 0)} przepisów")
        
        for category, recipes in result.get('by_category', {}).items():
            print(f"\n📂 {category.upper()}:")
            for recipe in recipes[:2]:  # pokaż 2 z każdej kategorii
                print(f"  - {recipe['title']}")
        
        print("\n🔍 Test 2: Kategoria wege")
        result2 = rag.suggest_recipes(['tofu', 'papryka'], category='wege')
        print(f"Znaleziono przepisów wege: {result2.get('found_recipes', 0)}")
        
        print("\n🔍 Test 3: Nieistniejące składniki")
        result3 = rag.suggest_recipes(['ananas', 'czekolada'])
        if 'message' in result3:
            print(f"Brak wyników: {result3['message']}")
    
    print("\n✅ Test RAG zakończony")