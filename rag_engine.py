import json
from typing import List, Dict, Any, Optional


class CocktailRetriever:
    """
    Handles loading and searching data from the cocktail_dataset.json file.
    This is the "Retrieval" component in our RAG system.
    """

    def __init__(self, db_path: str):
        """
        Initializes the retriever by loading data from the specified path.
        """
        try:
            with open(db_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            print(f"Successfully loaded {len(self.data)} cocktails from {db_path}")
        except FileNotFoundError:
            print(f"ERROR: Database file not found: {db_path}")
            self.data = []
        except json.JSONDecodeError:
            print(f"ERROR: Could not decode JSON file: {db_path}")
            self.data = []
        except Exception as e:
            print(f"ERROR: An unexpected error occurred while loading data: {e}")
            self.data = []

    @staticmethod
    def _simplify_cocktail(cocktail: Dict[str, Any]) -> Dict[str, Any]:
        """
        A private helper method to format the output for the LLM.
        """
        ingredients_list = []
        for ing in cocktail.get('ingredients') or []:
            measure = ing.get('measure', '').strip()
            name = ing.get('name', '').strip()
            ingredients_list.append(f"{measure} {name}".strip())

        return {
            "name": cocktail.get('name'),
            "category": cocktail.get('category'),
            "glass": cocktail.get('glass'),
            "instructions": cocktail.get('instructions'),
            "tags": cocktail.get('tags') or [],
            "ingredients": ingredients_list
        }

    @staticmethod
    def _normalize_ingredient(name: str) -> str:
        """
        Simplifies ingredient names for searching.
        Groups synonyms (e.g., "Lemon Juice" and "lemon")
        and differentiates special cases (e.g., "Lemon Peel").
        """
        name_lower = name.lower().strip()

        if "lemon peel" in name_lower:
            return "lemon peel"
        if "lemonade" in name_lower:
            return "lemonade"

        if "lemon" in name_lower or "lemon juice" in name_lower:
            return "lemon"
        if "lime" in name_lower or "lime juice" in name_lower:
            return "lime"

        if "sugar" in name_lower:
            return "sugar"

        if "light rum" in name_lower:
            return "light rum"
        if "rum" in name_lower:
            return "rum"

        return name_lower

    def find_cocktail_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Finds a cocktail by name (exact and partial match).
        """
        if not self.data:
            return None

        for cocktail in self.data:
            if name.lower() == cocktail['name'].lower():
                return self._simplify_cocktail(cocktail)

        for cocktail in self.data:
            if name.lower() in cocktail['name'].lower():
                return self._simplify_cocktail(cocktail)

        return None

    def find_cocktails_by_ingredients(self, ingredients: List[str]) -> Dict[str, List]:
        """
        Finds cocktails based on a list of ingredients.
        Returns a dictionary with two lists: 'perfect' and 'partial'.
        """
        if not self.data:
            return {"perfect": [], "partial": []}

        matches = []
        normalized_user_ingredients = {self._normalize_ingredient(ing) for ing in ingredients}
        num_user_ingredients = len(normalized_user_ingredients)

        for cocktail in self.data:
            cocktail_ingredients_set = {
                self._normalize_ingredient(ing['name'])
                for ing in cocktail.get('ingredients') or []
            }

            matched_ingredients = normalized_user_ingredients.intersection(cocktail_ingredients_set)

            if "rum" in normalized_user_ingredients and "light rum" in cocktail_ingredients_set:
                matched_ingredients.add("rum (as light rum)")

            match_count = len(matched_ingredients)

            if match_count > 0:
                match_type = "partial"
                if normalized_user_ingredients.issubset(cocktail_ingredients_set):
                    match_type = "perfect"

                matches.append({
                    "cocktail": self._simplify_cocktail(cocktail),
                    "match_count": match_count,
                    "total_user_ingredients": num_user_ingredients,
                    "match_type": match_type,
                    "matched_ingredients": list(matched_ingredients),
                    "total_ingredients_in_cocktail": len(cocktail_ingredients_set)
                })

        sorted_matches = sorted(matches, key=lambda x: x['match_count'], reverse=True)

        perfect_matches = [m for m in sorted_matches if m['match_type'] == 'perfect']
        partial_matches = [m for m in sorted_matches if m['match_type'] == 'partial' and m not in perfect_matches][:5]

        return {"perfect": perfect_matches, "partial": partial_matches}

    def find_cocktails_by_tags(self, tags: List[str]) -> List[Dict[str, Any]]:
        """
        Finds cocktails based on tags/preferences.
        Requires the cocktail to have ALL provided tags.
        """
        if not self.data:
            return []

        matches = []
        lower_tags_set = {tag.lower() for tag in tags}

        for cocktail in self.data:
            cocktail_tags = cocktail.get('tags') or []
            cocktail_tags_set = {tag.lower() for tag in cocktail_tags}

            if lower_tags_set.issubset(cocktail_tags_set):
                matches.append(self._simplify_cocktail(cocktail))

            if len(matches) >= 5:
                break

        return matches