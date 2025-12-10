"""
Local Voice Testing for Absher Assistant - Sam
Microphone ↔ Voice (without Twilio)
All prints in English
"""

import os
import sys
import platform
import tempfile
from datetime import datetime
from pathlib import Path

# Check audio libraries
try:
    import sounddevice as sd
    from scipy.io.wavfile import write as write_wav
    import numpy as np
except ImportError:
    print("ERROR: Audio libraries not installed!")
    print("\nInstall them with:")
    print("pip install sounddevice scipy numpy")
    sys.exit(1)

# Import local modules
try:
    from config import *
    from assistant import SmartAssistant, generate_response
    from data import get_user_by_phone, get_expiring_documents, MOCK_USERS
    from prompts import get_greeting
    from openai import OpenAI
except ImportError as e:
    print(f"ERROR: Import failed: {e}")
    print("Make sure all required files exist")
    sys.exit(1)

# ==========================
# Audio Settings
# ==========================
SAMPLE_RATE = 16000
RECORDING_DURATION = 5  # seconds
AUDIO_FOLDER = "audio_files"

# Create audio folder
Path(AUDIO_FOLDER).mkdir(exist_ok=True)

# Initialize OpenAI
if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY not found in .env file")
    sys.exit(1)

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ==========================
# Colors
# ==========================
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_colored(text, color=""):
    """Print colored text"""
    try:
        print(f"{color}{text}{Colors.RESET}")
    except:
        print(text)

def print_header():
    """Print header"""
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print_colored("\n" + "="*70, Colors.CYAN)
    print_colored("🎤 Absher Voice Assistant - Sam", Colors.BOLD + Colors.BLUE)
    print_colored("    Local Voice Testing Version", Colors.CYAN)
    print_colored("="*70, Colors.CYAN)
    print_colored(f"\n💻 System: {platform.system()}", Colors.YELLOW)
    print_colored(f"🎤 Sample Rate: {SAMPLE_RATE} Hz", Colors.YELLOW)
    print_colored(f"⏱️  Recording Duration: {RECORDING_DURATION} seconds", Colors.YELLOW)
    print_colored("="*70 + "\n", Colors.CYAN)

def print_status(message, status="info"):
    """Print status message"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    if status == "info":
        print_colored(f"[{timestamp}] ℹ️  {message}", Colors.CYAN)
    elif status == "success":
        print_colored(f"[{timestamp}] ✅ {message}", Colors.GREEN)
    elif status == "error":
        print_colored(f"[{timestamp}] ❌ {message}", Colors.RED)
    elif status == "warning":
        print_colored(f"[{timestamp}] ⚠️  {message}", Colors.YELLOW)
    elif status == "recording":
        print_colored(f"[{timestamp}] 🎤 {message}", Colors.MAGENTA)
    elif status == "speaking":
        print_colored(f"[{timestamp}] 🔊 {message}", Colors.BLUE)

# ==========================
# Audio Recording
# ==========================
def record_audio(duration=RECORDING_DURATION, show_countdown=True):
    """Record audio from microphone"""
    
    try:
        if show_countdown:
            print_status("Get ready to speak...", "warning")
            for i in range(3, 0, -1):
                print(f"   {i}...", end=" ", flush=True)
                import time
                time.sleep(0.8)
            print()
        
        print_status(f"🎤 RECORDING NOW! ({duration} seconds)", "recording")
        
        # Record
        audio = sd.rec(
            int(duration * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='int16'
        )
        sd.wait()
        
        # Save file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(AUDIO_FOLDER, f"user_{timestamp}.wav")
        write_wav(filename, SAMPLE_RATE, audio)
        
        print_status("Recording completed successfully", "success")
        return filename
        
    except Exception as e:
        print_status(f"Recording error: {e}", "error")
        return None

# ==========================
# Speech to Text
# ==========================
def speech_to_text(audio_path):
    """Convert audio file to text using Whisper"""
    
    if not audio_path or not os.path.exists(audio_path):
        return ""
    
    try:
        print_status("Converting speech to text...", "info")
        
        with open(audio_path, "rb") as audio_file:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ar",
                response_format="text"
            )
        
        text = transcript.strip()
        
        if text:
            print_colored(f"\n👤 You said: \"{text}\"", Colors.GREEN)
            print_status("Conversion successful", "success")
        else:
            print_status("Could not understand any clear speech", "warning")
        
        return text
        
    except Exception as e:
        print_status(f"Conversion error: {e}", "error")
        return ""

# ==========================
# Text to Speech
# ==========================
def text_to_speech(text, play=True):
    """Convert text to speech using OpenAI TTS"""
    
    try:
        print_status("Converting text to speech...", "info")
        
        # Convert text to speech
        response = openai_client.audio.speech.create(
            model="tts-1-hd",
            voice="nova",  # Natural female voice
            input=text,
            speed=0.95  # Slightly slower for elderly
        )
        
        # Save file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(AUDIO_FOLDER, f"assistant_{timestamp}.mp3")
        
        audio_data = response.read()
        with open(filename, "wb") as f:
            f.write(audio_data)
        
        print_status("Conversion successful", "success")
        
        # Play audio
        if play:
            play_audio(filename)
        
        return filename
        
    except Exception as e:
        print_status(f"Text conversion error: {e}", "error")
        return None

# ==========================
# Play Audio
# ==========================
def play_audio(audio_path):
    """Play audio file"""
    
    try:
        print_status("🔊 Playing audio...", "speaking")
        
        system = platform.system()
        
        if system == "Darwin":  # macOS
            os.system(f"afplay '{audio_path}'")
        elif system == "Windows":
            os.system(f'start /min "" "{audio_path}"')
            import time
            time.sleep(3)  # Wait for playback
        elif system == "Linux":
            os.system(f"aplay '{audio_path}' 2>/dev/null || mpg123 '{audio_path}' 2>/dev/null")
        
        print_status("Playback finished", "success")
        
    except Exception as e:
        print_status(f"Playback error: {e}", "error")

# ==========================
# User Selection
# ==========================
def select_user():
    """Select test user"""
    print_colored("\n👥 Available Test Users:", Colors.CYAN)
    
    users_list = []
    for phone, user in MOCK_USERS.items():
        users_list.append({
            "phone": phone,
            "name": user.get("name"),
            "nickname": user.get("nickname")
        })
    
    for i, user in enumerate(users_list, 1):
        print(f"   {i}. {user['name']} ({user['nickname']}) - {user['phone']}")
    
    print(f"   0. Continue without identification")
    print()
    
    choice = input(f"{Colors.YELLOW}Select number (0-{len(MOCK_USERS)}): {Colors.RESET}").strip()
    
    if choice == "0":
        return None
    
    try:
        idx = int(choice) - 1
        users_list_phones = list(MOCK_USERS.keys())
        if 0 <= idx < len(users_list_phones):
            return users_list_phones[idx]
    except:
        pass
    
    return None

# ==========================
# Voice Chat Loop
# ==========================
def voice_chat_loop():
    """Main voice conversation loop"""
    
    print_header()
    
    print_colored("💡 Instructions:", Colors.YELLOW)
    print("   • Press Enter to start recording")
    print("   • Speak clearly after countdown")
    print("   • Say 'Thank you' or 'Goodbye' to end")
    print("   • Press Ctrl+C to exit immediately")
    print_colored("="*70 + "\n", Colors.CYAN)
    
    # Select user
    phone_number = select_user()
    
    # Initialize assistant
    assistant = SmartAssistant(phone_number)
    
    # Show user info
    if assistant.user:
        user = assistant.user
        print_colored(f"\n✅ Identified: {user.get('name')} ({user.get('nickname')})", Colors.GREEN)
        wallet = user.get('family_wallet', {}).get('balance', 0)
        print_colored(f"💰 Wallet Balance: {wallet} SAR\n", Colors.CYAN)
    
    # Conversation history
    history = []
    turn_count = 0
    
    # Greeting
    greeting = assistant.get_greeting()
    print_colored("\n🤖 Sam:", Colors.BLUE)
    print(f"  {greeting}\n")
    text_to_speech(greeting)
    
    while True:
        try:
            turn_count += 1
            print_colored(f"\n{'='*70}", Colors.CYAN)
            print_colored(f"🔄 Turn #{turn_count}", Colors.CYAN)
            print_colored(f"{'='*70}\n", Colors.CYAN)
            
            # Wait for user
            input(f"{Colors.GREEN}Press Enter to speak... {Colors.RESET}")
            
            # Record user audio
            audio_file = record_audio(show_countdown=True)
            
            if not audio_file:
                print_status("Recording failed, try again", "error")
                continue
            
            # Convert speech to text
            user_text = speech_to_text(audio_file)
            
            if not user_text:
                print_status("Could not understand, please repeat", "warning")
                text_to_speech("I didn't hear anything clear. Can you repeat louder?")
                continue
            
            # Check exit keywords
            if any(keyword in user_text.lower() for keyword in EXIT_KEYWORDS):
                print_colored(f"\n🤖 Sam:", Colors.BLUE)
                from prompts import FAREWELL_MESSAGE
                print(f"  {FAREWELL_MESSAGE}\n")
                text_to_speech(FAREWELL_MESSAGE)
                
                print_colored(f"\n✅ Conversation ended after {turn_count} turns", Colors.GREEN)
                print_colored("👋 Goodbye!\n", Colors.YELLOW)
                break
            
            # Handle requests
            if any(word in user_text.lower() for word in ["جديد", "عندي من", "وش عندي"]):
                print_status("Checking documents...", "info")
                reply = assistant.handle_whats_new()
            elif any(word in user_text.lower() for word in ["جدد", "تجديد", "نعم", "أيوه"]):
                print_status("Processing renewal...", "info")
                reply = assistant.handle_renewal_request(user_text)
            elif any(word in user_text.lower() for word in ["محفظة", "رصيد"]):
                reply = assistant.handle_wallet_inquiry()
            elif any(word in user_text.lower() for word in ["ذكرني", "تذكير"]):
                print_status("Setting reminder...", "info")
                reply = assistant.handle_reminder_request()
            else:
                print_status("Sam is thinking...", "info")
                reply = generate_response(user_text, phone_number, history)
            
            # Display response
            print_colored(f"\n🤖 Sam:", Colors.BLUE)
            print(f"  {reply}\n")
            
            # Convert and play response
            text_to_speech(reply)
            
            # Save history
            history.append({"role": "user", "content": user_text})
            history.append({"role": "assistant", "content": reply})
            
            # Limit history
            if len(history) > MAX_CONVERSATION_HISTORY:
                history = history[-MAX_CONVERSATION_HISTORY:]
                
        except KeyboardInterrupt:
            print_colored("\n\n⚠️ Program interrupted (Ctrl+C)", Colors.YELLOW)
            print_colored("👋 Goodbye!\n", Colors.CYAN)
            break
        except Exception as e:
            print_status(f"Error: {e}", "error")
            print_colored("💡 Try again\n", Colors.YELLOW)

# ==========================
# Device Testing
# ==========================
def test_devices():
    """Test microphone and speakers"""
    
    print_colored("\n🧪 Testing Devices...\n", Colors.YELLOW)
    
    # Show available devices
    print_colored("🎤 Available Input Devices:", Colors.CYAN)
    devices = sd.query_devices()
    
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            print(f"   [{i}] {device['name']}")
    
    print_colored("\n🔊 Available Output Devices:", Colors.CYAN)
    for i, device in enumerate(devices):
        if device['max_output_channels'] > 0:
            print(f"   [{i}] {device['name']}")
    
    # Test microphone
    print_colored("\n🧪 Microphone Test...", Colors.YELLOW)
    choice = input("Test microphone? (y/n): ").lower()
    
    if choice == 'y':
        print_status("Record a short message...", "recording")
        test_audio = record_audio(duration=3, show_countdown=True)
        
        if test_audio:
            print_status("Playing recording...", "speaking")
            play_audio(test_audio)
            print_status("Microphone test completed", "success")

# ==========================
# Entry Point
# ==========================
def main():
    """Main function"""
    
    # Validate config
    if not validate_config():
        print_colored("\n⚠️ Some settings are missing", Colors.YELLOW)
        choice = input("\nContinue anyway? (y/n): ").lower()
        if choice != 'y':
            sys.exit(0)
    
    # Show menu
    print_colored("\n🎯 Select Mode:", Colors.CYAN)
    print("   1. Start Voice Conversation")
    print("   2. Test Devices")
    print("   3. Exit")
    
    choice = input("\nYour choice (1-3): ").strip()
    
    if choice == "1":
        voice_chat_loop()
    elif choice == "2":
        test_devices()
        print()
        main()  # Return to menu
    else:
        print_colored("\n👋 Goodbye!\n", Colors.YELLOW)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print_colored(f"\n❌ Fatal error: {e}", Colors.RED)
        sys.exit(1)