"""
Title: Main for Video Game Expert Bot,
Author: Camden Konopka, Benjamin Dealy and Fionn Darcy,
Description: Main file to run the Video Game Expert Bot, imports GUI and user input handler,
"""

# Import the custom function that builds and displays the graphical user interface
from chat_GUI import create_chat_gui

# Standard Python boilerplate: ensures the code only runs if this specific file is executed directly
# (and not imported as a module in another script)
if __name__ == "__main__":
    # Launch the chatbot window
    create_chat_gui()
