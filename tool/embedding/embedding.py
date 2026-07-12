from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from services.model import embedding, model
from langchain_core.tools import create_retriever_tool
from langchain.agents import create_agent
from langchain_core.documents import Document
from langchain.messages import AIMessage

from services.uicli import print_ai_response, print_documents

# Gemini Developer API
# embeddings = GoogleGenerativeAIEmbeddings(
#     model="gemini-embedding-001",
#     api_key=API_KEY
# )

texts = [
    """
    Apple is one of the world's most popular fruits. It is sweet, crunchy,
    and available in many varieties such as Fuji, Gala, Honeycrisp, and Granny Smith.
    Apples are rich in dietary fiber, vitamin C, antioxidants, and potassium.
    Eating apples regularly may improve heart health, digestion, and immune function.
    Many people enjoy eating apples raw, in salads, juices, pies, and desserts.
    User opinion: I absolutely love apples and eat one almost every day.
    """,
    """
    Orange is a citrus fruit known for its refreshing taste and high vitamin C content.
    Oranges are an excellent source of antioxidants, fiber, and folate.
    Drinking fresh orange juice is popular around the world.
    Oranges help improve immunity and skin health.
    User opinion: I enjoy oranges, especially during summer.
    """,
    """
    Pear is a soft, juicy fruit with a naturally sweet flavor.
    Pears contain dietary fiber, vitamin K, copper, and vitamin C.
    They support healthy digestion and may reduce inflammation.
    Pears can be eaten fresh, baked, or added to desserts.
    User opinion: I think pears are delicious and underrated.
    """,
    """
    Banana is among the most consumed fruits worldwide.
    It is rich in potassium, vitamin B6, magnesium, and carbohydrates.
    Bananas provide quick energy and are widely eaten before workouts.
    They are commonly used in smoothies, cakes, and breakfast meals.
    User opinion: I don't enjoy bananas because they become too soft when ripe.
    """,
    """
    Mango is often called the king of fruits.
    It has a sweet tropical flavor and contains vitamins A, C, and E.
    Mangoes are commonly used in juices, desserts, smoothies, and salads.
    User opinion: I love mangoes and always wait for mango season.
    """,
    """
    Grapes grow in clusters and come in green, red, and black varieties.
    They are rich in antioxidants like resveratrol.
    Grapes are used for fresh eating, raisins, juices, and wine production.
    User opinion: Grapes are good, but I don't eat them often.
    """,
    """
    Watermelon is a large fruit with high water content.
    It helps maintain hydration and contains vitamins A and C.
    Watermelon is especially popular during hot summer months.
    User opinion: Watermelon is refreshing and one of my favorite summer fruits.
    """,
    """
    Strawberry is a bright red fruit rich in vitamin C, manganese,
    and antioxidants. It is commonly used in desserts, cakes,
    milkshakes, and jams.
    User opinion: I dislike strawberries because of their tiny seeds.
    """,
    """
    Apple Inc. is a multinational technology company headquartered in Cupertino, California.
    Apple designs and manufactures products such as the iPhone, MacBook, iPad,
    Apple Watch, and AirPods. Its operating systems include iOS, macOS,
    watchOS, and iPadOS. Apple is recognized for innovation,
    premium hardware, and a tightly integrated ecosystem.
    """,
    """
    MacBook is Apple's laptop lineup.
    Models include the MacBook Air and MacBook Pro.
    They are powered by Apple Silicon processors such as M1, M2, M3, and M4.
    MacBooks are known for excellent battery life, quiet operation,
    and high-quality displays.
    User opinion: I am a huge fan of the MacBook because of its battery life and performance.
    """,
    """
    Lenovo is one of the world's largest computer manufacturers.
    It produces ThinkPad, IdeaPad, Yoga, and Legion laptops.
    ThinkPads are widely used by software engineers because of their
    keyboard quality, durability, and Linux compatibility.
    User opinion: I also like Lenovo laptops, especially the ThinkPad series.
    """,
    """
    Fruit preference summary:
    Favorite fruits:
    - Apple
    - Mango
    - Orange
    - Watermelon

    Neutral:
    - Grapes

    Disliked:
    - Banana
    - Strawberry

    Favorite laptop brands:
    - Apple MacBook
    - Lenovo ThinkPad
    """,
]
# from langchain_core.documents import Document

documents = [
    Document(
        page_content="""
Apple is one of the most popular fruits in the world. It grows on apple trees and comes in many varieties,
including Fuji, Gala, Honeycrisp, Red Delicious, and Granny Smith.

Apples are rich in dietary fiber, vitamin C, potassium, and antioxidants. Regular consumption of apples
may support heart health, improve digestion, strengthen the immune system, and help maintain healthy blood sugar levels.

Apples are commonly eaten raw but are also used in juices, pies, cakes, salads, jams, and desserts.

User Preference:
The user loves apples and usually eats one every day. Apples are considered the user's favorite fruit.
""",
        metadata={
            "id": 1,
            "category": "fruit",
            "title": "Apple",
            "source": "knowledge_base",
        },
    ),
    Document(
        page_content="""
Orange is a citrus fruit famous for its sweet and slightly tangy taste.
It is one of the richest natural sources of vitamin C and contains antioxidants,
fiber, folate, and potassium.

Eating oranges regularly can improve immunity, skin health, and heart health.
Orange juice is one of the most popular breakfast drinks worldwide.

User Preference:
The user enjoys oranges, especially during the summer season.
""",
        metadata={
            "id": 2,
            "category": "fruit",
            "title": "Orange",
            "source": "knowledge_base",
        },
    ),
    Document(
        page_content="""
Banana is one of the world's most consumed fruits.
It is rich in potassium, magnesium, vitamin B6, and carbohydrates.

Bananas provide quick energy and are commonly eaten before workouts.
They are used in smoothies, cakes, desserts, and breakfast meals.

User Preference:
The user dislikes bananas because they become too soft after ripening.
""",
        metadata={
            "id": 3,
            "category": "fruit",
            "title": "Banana",
            "source": "knowledge_base",
        },
    ),
    Document(
        page_content="""
Pear is a sweet, juicy fruit available in green, yellow, and red varieties.
Pears are rich in dietary fiber, vitamin C, vitamin K, and copper.

Regular consumption of pears supports digestion and gut health.

User Preference:
The user thinks pears are delicious and enjoys eating them fresh.
""",
        metadata={
            "id": 4,
            "category": "fruit",
            "title": "Pear",
            "source": "knowledge_base",
        },
    ),
    Document(
        page_content="""
Mango is known as the king of fruits in many countries.
It has a sweet tropical flavor and is rich in vitamins A, C, E, antioxidants, and dietary fiber.

Mangoes are widely used in juices, desserts, milkshakes, ice cream, and salads.

User Preference:
The user loves mangoes and eagerly waits for mango season every year.
""",
        metadata={
            "id": 5,
            "category": "fruit",
            "title": "Mango",
            "source": "knowledge_base",
        },
    ),
    Document(
        page_content="""
Watermelon is a refreshing fruit with over 90 percent water content.
It contains vitamins A, C, and lycopene.

Watermelon is especially popular during hot summer months because it helps prevent dehydration.

User Preference:
The user enjoys watermelon during the summer and considers it one of the most refreshing fruits.
""",
        metadata={
            "id": 6,
            "category": "fruit",
            "title": "Watermelon",
            "source": "knowledge_base",
        },
    ),
    Document(
        page_content="""
Strawberry is a bright red fruit known for its sweet taste and aroma.
It contains vitamin C, manganese, antioxidants, and dietary fiber.

Strawberries are commonly used in cakes, desserts, jams, milkshakes, and ice cream.

User Preference:
The user dislikes strawberries because of the tiny seeds on their surface.
""",
        metadata={
            "id": 7,
            "category": "fruit",
            "title": "Strawberry",
            "source": "knowledge_base",
        },
    ),
    Document(
        page_content="""
Apple Inc. is an American multinational technology company headquartered in Cupertino, California.

Apple develops products including:
- iPhone
- MacBook Air
- MacBook Pro
- iPad
- Apple Watch
- AirPods

Apple also develops software including:
- iOS
- macOS
- watchOS
- iPadOS

Apple is known for premium hardware, excellent software integration,
high performance, privacy, and innovation.

User Preference:
The user is a huge fan of Apple products, especially the MacBook series.
""",
        metadata={
            "id": 8,
            "category": "company",
            "title": "Apple Inc.",
            "source": "knowledge_base",
        },
    ),
    Document(
        page_content="""
MacBook is Apple's premium laptop lineup.

Popular models include:
- MacBook Air
- MacBook Pro

Modern MacBooks use Apple Silicon processors such as:
- M1
- M2
- M3
- M4

MacBooks are known for:
- Excellent battery life
- Silent operation
- Premium display
- Lightweight design
- Outstanding performance

User Preference:
The user prefers MacBooks for software development because of their battery life and build quality.
""",
        metadata={
            "id": 9,
            "category": "laptop",
            "title": "MacBook",
            "source": "knowledge_base",
        },
    ),
    Document(
        page_content="""
Lenovo is one of the largest computer manufacturers in the world.

Its laptop lineup includes:
- ThinkPad
- IdeaPad
- Legion
- Yoga

ThinkPads are popular among software engineers because of:
- Excellent keyboard
- Linux compatibility
- Durability
- Business features

User Preference:
The user also likes Lenovo ThinkPads and considers them excellent programming laptops.
""",
        metadata={
            "id": 10,
            "category": "laptop",
            "title": "Lenovo",
            "source": "knowledge_base",
        },
    ),
    Document(
        page_content="""
User Preference Summary

Favorite Fruits:
- Apple
- Mango
- Orange
- Watermelon

Neutral Fruits:
- Pear

Disliked Fruits:
- Banana
- Strawberry

Favorite Technology Brands:
- Apple
- Lenovo

Favorite Laptop:
- MacBook Pro

Programming Interests:
- Python
- AI
- LangChain
- LangGraph
- Full Stack Development
""",
        metadata={
            "id": 11,
            "category": "user_profile",
            "title": "User Preferences",
            "source": "knowledge_base",
        },
    ),
]

vector_store = FAISS.from_documents(documents, embedding)
print_documents(vector_store, "What is apple?", 7)

print_documents(vector_store, "Linux is great Operating System", 4)

print_documents(vector_store, "What are some fruits?", 7)


retriver = vector_store.as_retriever(search_kwargs={"k": 7})
retriver_tool = create_retriever_tool(
    retriver, name="kb_search", description="Search the knowledge base for information."
)

agent = create_agent(
    model=model,
    tools=[retriver_tool],
    system_prompt="""
You are a helpful assistant.

For every question related to Apple, laptops, computers, or fruits:

1. Always call kb_search first.
2. Retrieve the most relevant documents.
3. Use only the retrieved information.
4. If the documents don't contain the answer, say you don't know.
5. You may call kb_search multiple times if needed.
""",
)

result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": (
                    "What are the three most popular fruits? "
                    "What are their characteristics? "
                    "Which three fruits does the user dislike?"
                ),
            }
        ]
    }
)

# print(result["messages"][-1].content)
# print(result["messages"][-1].content)
print_ai_response(result)
