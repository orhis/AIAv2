# core/rag/recipe_loader.py
import json
import os
from typing import List, Dict, Any

class RecipeLoader:
    """Klasa do wczytywania i przetwarzania przepisów oraz składników"""
    
    def __init__(self, base_path: str = "data/recipes"):
        self.base_path = base_path
        self.recipes = []
        self.skladniki = {}
        
    def load_recipes(self, filename: str = "recipes_100.json") -> List[Dict]:
        """Wczytuje przepisy z pliku JSON"""
        try:
            file_path = os.path.join(self.base_path, filename)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                self.recipes = json.load(f)
            
            print(f"✅ Wczytano {len(self.recipes)} przepisów z {filename}")
            return self.recipes
            
        except FileNotFoundError:
            print(f"❌ Nie znaleziono pliku: {file_path}")
            return []
        except json.JSONDecodeError as e:
            print(f"❌ Błąd parsowania JSON: {e}")
            return []
        except Exception as e:
            print(f"❌ Nieoczekiwany błąd: {e}")
            return []
    
    def load_skladniki(self, filename: str = "skladniki_baza.json") -> Dict:
        """Wczytuje bazę składników"""
        try:
            file_path = os.path.join(self.base_path, filename)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.skladniki = {s['nazwa']: s for s in data['skladniki']}
            
            print(f"✅ Wczytano {len(self.skladniki)} składników")
            return self.skladniki
            
        except Exception as e:
            print(f"❌ Błąd wczytywania składników: {e}")
            return {}
    
    def parse_ingredients(self, ingredients_str: str) -> List[str]:
        """Parsuje string składników na listę"""
        ingredients = [ing.strip() for ing in ingredients_str.split(',')]
        return [ing for ing in ingredients if ing]  # usuń puste
    
    def get_recipe_by_category(self, category: str) -> List[Dict]:
        """Zwraca przepisy z określonej kategorii"""
        return [r for r in self.recipes if r.get('category') == category]
    
    def get_recipes_with_ingredients(self, required_ingredients: List[str]) -> List[Dict]:
        """Znajdź przepisy zawierające podane składniki"""
        matching_recipes = []
        
        for recipe in self.recipes:
            recipe_ingredients = self.parse_ingredients(recipe['ingredients'])
            
            # Sprawdź czy przepis zawiera którykolwiek z wymaganych składników
            if any(req_ing.lower() in [ing.lower() for ing in recipe_ingredients] 
                   for req_ing in required_ingredients):
                matching_recipes.append(recipe)
        
        return matching_recipes
    
    def get_stats(self) -> Dict[str, Any]:
        """Zwraca statystyki bazy danych"""
        if not self.recipes:
            return {"error": "Brak wczytanych przepisów"}
        
        categories = {}
        all_ingredients = set()
        
        for recipe in self.recipes:
            # Statystyki kategorii
            cat = recipe.get('category', 'unknown')
            categories[cat] = categories.get(cat, 0) + 1
            
            # Wszystkie składniki
            ingredients = self.parse_ingredients(recipe['ingredients'])
            all_ingredients.update(ing.lower() for ing in ingredients)
        
        return {
            "total_recipes": len(self.recipes),
            "categories": categories,
            "unique_ingredients": len(all_ingredients),
            "ingredients_list": sorted(list(all_ingredients))
        }

# === Test lokalny ===
if __name__ == "__main__":
    print("🧪 Test Recipe Loader")
    
    # Inicjalizacja
    loader = RecipeLoader()
    
    # Wczytaj dane
    recipes = loader.load_recipes()
    skladniki = loader.load_skladniki()
    
    if recipes:
        # Pokaż statystyki
        stats = loader.get_stats()
        print(f"\n📊 Statystyki:")
        print(f"Przepisy: {stats['total_recipes']}")
        print(f"Kategorie: {stats['categories']}")
        print(f"Unikalne składniki: {stats['unique_ingredients']}")
        
        # Test wyszukiwania
        print(f"\n🔍 Test: przepisy z jajkami")
        egg_recipes = loader.get_recipes_with_ingredients(['jajka'])
        for recipe in egg_recipes[:3]:  # pokaż pierwsze 3
            print(f"- {recipe['title']} ({recipe['category']})")
        
        # Test kategorii
        print(f"\n🥬 Przepisy wege:")
        vege_recipes = loader.get_recipe_by_category('wege')
        print(f"Znaleziono {len(vege_recipes)} przepisów wege")
    
    print("\n✅ Test zakończony")