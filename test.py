from huggingface_hub import InferenceClient

client = InferenceClient(
    provider="hf-inference",
    api_key="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",
)

result = client.text_classification(
    "I like you. I love you",
    model="ProsusAI/finbert",
)