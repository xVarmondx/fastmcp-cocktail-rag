from fastmcp import FastMCP
from typing import List, Dict, Any
from rag_engine import CocktailRetriever

mcp = FastMCP(
    name="CocktailRAGAssistant",
    instructions="""
    You are a bartender assistant. Your sole task is to answer user questions
    EXCLUSIVELY using the provided tools.

    RULES:
    1. NEVER answer based on your own built-in knowledge.
    2. ALWAYS analyze the user's query and match it to one of the available tools.
    3. ALWAYS ask the user for permission ("May I use tool X to...") before executing a tool.
    4. If the user asks for a recipe or ingredients, you MUST use a tool.
    5. If no tool matches the query, reply: "Sorry, I cannot help with this query as I do not have the appropriate tool."
    6. Always respond in English.
    """
)

try:
    retriever = CocktailRetriever(db_path="dataset/cocktail_dataset.json")
except Exception as e:
    print(f"Failed to load retriever: {e}")
    retriever = None


def create_error_response(message: str) -> Dict[str, Any]:
    """Creates a standardized error response in JSON format."""
    return {
        "status": "error",
        "message": message
    }


@mcp.tool
def get_cocktail_recipe(cocktail_name: str) -> Dict[str, Any]:
    """
    Gets the recipe and details for one specific cocktail by its name.
    Use this tool if the user asks for a specific cocktail recipe.

    :param cocktail_name: The name of the cocktail to search for (e.g., "Mojito", "Old Fashioned").
    :return: A dictionary with cocktail details or an error dictionary.
    """
    if not retriever or not retriever.data:
        return create_error_response("Server Error: The cocktail database is not loaded.")

    print(f"Tool [get_cocktail_recipe] called with query: {cocktail_name}")
    result = retriever.find_cocktail_by_name(cocktail_name)

    if result:
        return {
            "status": "success",
            "type": "recipe",
            "data": result
        }
    else:
        return create_error_response(f"Sorry, I could not find a cocktail named '{cocktail_name}'.")


@mcp.tool
def suggest_cocktails_by_ingredients(ingredients: List[str]) -> Dict[str, Any]:
    """
    Suggests cocktails based on a list of ingredients the user HAS.

    :param ingredients: A list of ingredient names (e.g., ["Rum", "Lime", "Mint", "Sugar"]).
    :return: A dictionary with suggested cocktails or an error dictionary.
    """
    if not retriever or not retriever.data:
        return create_error_response("Server Error: The cocktail database is not loaded.")

    print(f"Tool [suggest_cocktails_by_ingredients] called with ingredients: {ingredients}")
    results = retriever.find_cocktails_by_ingredients(ingredients)

    perfect_list = []
    for item in results["perfect"]:
        perfect_list.append({
            "name": item["cocktail"]["name"],
            "matched_ingredients": item["matched_ingredients"],
            "all_ingredients_in_recipe": item["cocktail"]["ingredients"]
        })

    partial_list = []
    for item in results["partial"]:
        partial_list.append({
            "name": item["cocktail"]["name"],
            "matched_ingredients": item["matched_ingredients"],
            "missing_ingredients_count": item["total_user_ingredients"] - item["match_count"]
        })

    if not perfect_list and not partial_list:
        return create_error_response(
            f"Sorry, I couldn't find any cocktails matching the ingredients: {', '.join(ingredients)}.")
    else:
        return {
            "status": "success",
            "type": "suggestion_by_ingredient",
            "perfect_matches": perfect_list,
            "partial_matches": partial_list
        }


@mcp.tool
def suggest_cocktails_by_preference(preferences: List[str]) -> Dict[str, Any]:
    """
    Suggest cocktails matching a list of tags or preferences (e.g., "Classic", "Sour").
    The cocktail must match ALL provided preferences.

    :param preferences: A list of tags (e.g., "Classic", "IBA").
    :return: A dictionary with suggested cocktails or an error dictionary.
    """
    if not retriever or not retriever.data:
        return create_error_response("Server Error: The cocktail database is not loaded.")

    print(f"Tool [suggest_cocktails_by_preference] called with tags: {preferences}")
    results = retriever.find_cocktails_by_tags(preferences)

    if results:
        return {
            "status": "success",
            "type": "suggestion_by_preference",
            "count": len(results),
            "data": results
        }
    else:
        return create_error_response(
            f"Sorry, I couldn't find any cocktails matching the preferences: {', '.join(preferences)}.")


if __name__ == "__main__":
    if not retriever or not retriever.data:
        print(
            "WARNING: Server is starting, but the cocktail database was not loaded. Tools will not work.")

    print("Starting FastMCP Cocktail RAG server...")

    mcp.run(transport="http", host="127.0.0.1", port=8001)

    print("Server started.")