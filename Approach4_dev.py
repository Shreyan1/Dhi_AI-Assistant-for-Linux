"""
Project by Shreyan Basu Ray
Github : https://github.com/Shreyan1/Project-Dhi
LinkedIn : https://linkedin.com/in/shreyanbasuray
Year : 2024

Please feel free to collaborate on this.
Raise issues, PR, anything. I'll review them and fix right away.
--------------------------------------------------------------------
"""

## APPROACH 4 : USING A EMBEDDING UPDATE APPROACH TO UPDATE VECTORS BASED ON USER RESPONSE
 
import chromadb
from sentence_transformers import SentenceTransformer
import subprocess
import re
import numpy as np

# Suppressing warnings
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

persist_directory = "ChromaDB"

# Initialize Chroma client with persistence and get the collection
client = chromadb.PersistentClient(path=persist_directory)
collection = client.get_collection(name="commands")

# Initialize the sentence transformer for encoding
sentence_encoder = SentenceTransformer("all-MiniLM-L6-v2")

def find_closest_commands(user_input, n=6):
    results = collection.query(
        query_texts=[user_input],
        n_results=n
    )
    return list(zip(results['ids'], results['documents'][0], results['metadatas'][0], results['distances'][0]))


def update_embedding(command_id, user_input, is_positive):
    result = collection.get(ids=[command_id])
    if not result or 'embeddings' not in result or not result['embeddings']:
        print(f"No embedding found for command_id: {command_id}. Skipping update.")
        return
    
    current_embedding = result['embeddings'][0]
    user_embedding = sentence_encoder.encode([user_input])[0]
    
    if is_positive:
        new_embedding = 0.9 * np.array(current_embedding) + 0.1 * user_embedding
    else:
        new_embedding = 1.1 * np.array(current_embedding) - 0.1 * user_embedding

    new_embedding = new_embedding / np.linalg.norm(new_embedding)
    collection.update(ids=[command_id], embeddings=[new_embedding.tolist()])

def replace_placeholders(command):
    placeholders = re.findall(r'<(.*?)>', command)
    if placeholders:
        for placeholder in placeholders:
            if placeholder == "foldername":
                value = input(f"Enter {placeholder} [Note: for any top level directories, please declare as eg - /home, /var etc.] : ")
            else:
                value = input(f"Enter {placeholder}: ")
            command = command.replace(f"<{placeholder}>", value)
    return command

def execute_command(command):
    try:
        result = subprocess.run(command, 
                                shell=True,
                                check=True, text=True, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error executing command: {e.stderr}"

def confirm_match(closest_command, similarity):
    while True:
        try:
            confirmation = input(f"Closest match found: '{closest_command}' (Similarity: {(1-similarity)*100:.2f}%). \nIs this correct? (y/n ? Press q to quit): ")
        
            if confirmation.lower() == 'y':
                return True
            elif confirmation.lower() == 'n':
                return False
            elif confirmation.lower() == 'q':
                print("Exiting the program.")
                exit(0)
            else:
                print("Invalid input. Please enter 'y' for yes, 'n' for no, or 'q' to quit.")
        except KeyboardInterrupt:
            print("\nKeyboard interrupt detected. Exiting the program.")
            exit(0)

if __name__ == '__main__':
    try:
        while True:
            user_input = input("Enter your command: ").strip().lower()
            closest_commands = find_closest_commands(user_input)
            for command_id, natural_language, metadata, distance in closest_commands:
                try:
                    if confirm_match(natural_language, distance):
                        # Ensure command_id is a single string
                        update_embedding(str(command_id), user_input, is_positive=True)
                        command = metadata['command']
                        description = metadata['description']
                        print(f"Command from database: {command}")
                        print(f"Description: {description}")

                        command_with_values = replace_placeholders(command)
                        print(f"Command after placeholder replacement: {command_with_values}")

                        output = execute_command(command_with_values)
                        print("Command output:")
                        print(output)
                        break
                    else:
                        update_embedding(str(command_id), user_input, is_positive=False)

                except KeyboardInterrupt:
                    print("\nKeyboard interrupt detected. Moving to the next command.")
                    continue
            else:
                print("No more close matches found or none accepted.")
    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected. Exiting the program.")
