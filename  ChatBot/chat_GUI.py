"""
Title: Chat GUI for Video Game Expert Bot,
Author: Camden Konopka, Benjamin Dealy and Fionn Darcy,
Description: Creates the graphical user interface and links input/output,
"""

# Import tkinter for the window, scrolledtext for the history box, and our message handler
import tkinter as tk
from tkinter import scrolledtext
from user_input import send_message

def create_chat_gui():
    # Initialize the main window and set its title and starting size
    root = tk.Tk()
    root.title("Video Game Expert Bot")
    root.geometry("450x550")

    # Create the main chat history box with a scrollbar and word-wrapping
    chat_display = scrolledtext.ScrolledText(root, wrap=tk.WORD, state='disabled')
    chat_display.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    
    # Define a custom color tag to make the user's text appear blue
    chat_display.tag_configure("user_color", foreground="blue")
    
    # Temporarily enable the box to insert the initial "Welcome" message and instructions
    chat_display.configure(state='normal')
    chat_display.insert(tk.END,
        "Bot: Welcome to the Video Game Expert Bot!\n\n"
        "You can ask things like:\n"
        "- What is the best selling game?\n"
        "- When was Minecraft released?\n"
        "- Who published Elden Ring?\n"
        "- Tell me about Valorant\n"
        "- For more info please type 'help'\n\n"
    )
    # Set back to disabled so the user can't manually edit the chat history
    chat_display.configure(state='disabled')

    # Create the text box where the user types their questions
    user_entry = tk.Entry(root, font=("Arial", 12))
    user_entry.pack(padx=10, pady=5, fill=tk.X)
    
    # Bind the 'Enter' key so pressing it automatically triggers the send_message function
    user_entry.bind("<Return>", lambda event: send_message(user_entry, chat_display))

    # Add a green "Ask Bot" button that also triggers the send_message function when clicked
    tk.Button(root, text="Ask Bot", command=lambda: send_message(user_entry, chat_display), bg="#4CAF50", fg="white").pack(pady=10)

    # Start the application's event loop to keep the window open and responsive
    root.mainloop()
