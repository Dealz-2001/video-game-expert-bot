"""
Title: User Input Handler for Video Game Expert Bot,
Author: Camden Konopka, Benjamin Dealy and Fionn Darcy,
Description: Handles getting user input and generating bot responses
"""

# Import tkinter for GUI interaction and the custom logic function for generating answers
import tkinter as tk
from bot_logic import get_response

def send_message(user_entry, chat_display):
    """
    Retrieve user input from Entry widget, 
    send it to bot logic, and display the response.
    """
    # Get the text the user typed and remove any unnecessary leading/trailing spaces
    user_text = user_entry.get().strip()
    
    # Only proceed if the user actually typed something
    if user_text:
        # Temporarily enable the chat window so we can write to it
        chat_display.configure(state='normal')
        
        # Display the user's message at the end of the chat box
        chat_display.insert(tk.END, f"You: {user_text}\n", "user_color")
        
        # Pass the user's text to the bot_logic script to get the correct reply
        bot_reply = get_response(user_text)
        
        # Display the bot's calculated response
        chat_display.insert(tk.END, f"Bot: {bot_reply}\n\n")
        
        # Auto-scroll the window to the bottom so the newest message is always visible
        chat_display.see(tk.END)
        
        # Disable the chat window again to prevent the user from typing directly into the history
        chat_display.configure(state='disabled')
        
        # Clear the input box so the user can type their next question
        user_entry.delete(0, tk.END)

