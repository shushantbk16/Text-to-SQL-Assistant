from fastembed import TextEmbedding

print("Pre-downloading FastEmbed model...")
# This triggers the download and caching of the model
model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
print("Model downloaded successfully.")
