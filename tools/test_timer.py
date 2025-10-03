import time
import sys

class TelnetPrayerTimer:
    def __init__(self):
        # Each sublist represents syllables for one word
        self.prayer_syllables = [
            ["Our"],
            ["Fa", "ther,"],
            ["who"],
            ["art"],
            ["in"],
            ["hea", "ven,"],
            ["hal", "lowed"],
            ["be"],
            ["thy"],
            ["name;"],
            ["thy"],
            ["king", "dom"],
            ["come,"],
            ["thy"],
            ["will"],
            ["be"],
            ["done"],
            ["on"],
            ["earth"],
            ["as"],
            ["it"],
            ["is"],
            ["in"],
            ["hea", "ven."],
            ["Give"],
            ["us"],
            ["this"],
            ["day"],
            ["our"],
            ["dai", "ly"],
            ["bread,"],
            ["and"],
            ["for", "give"],
            ["us"],
            ["our"],
            ["tres", "pass", "es,"],
            ["as"],
            ["we"],
            ["for", "give"],
            ["those"],
            ["who"],
            ["tres", "pass"],
            ["a", "gainst"],
            ["us;"],
            ["and"],
            ["lead"],
            ["us"],
            ["not"],
            ["in", "to"],
            ["temp", "ta", "tion,"],
            ["but"],
            ["de", "liv", "er"],
            ["us"],
            ["from"],
            ["e", "vil."],
            ["A", "men."]
        ]
        
        # Full words for final output
        self.full_words = ["Our", "Father,", "who", "art", "in", "heaven,", 
                          "hallowed", "be", "thy", "name;", "thy", "kingdom", "come,",
                          "thy", "will", "be", "done", "on", "earth", "as", "it", "is",
                          "in", "heaven.", "Give", "us", "this", "day", "our", "daily",
                          "bread,", "and", "forgive", "us", "our", "trespasses,", "as",
                          "we", "forgive", "those", "who", "trespass", "against", "us;",
                          "and", "lead", "us", "not", "into", "temptation,", "but",
                          "deliver", "us", "from", "evil.", "Amen."]
        
        self.current_word = 0
        self.current_syllable = 0
        self.word_times = []
        self.syllable_times = []
        self.last_press = None
        self.started = False

    def display_prayer(self):
        """Display the prayer with current syllable marked."""
        print("\n" * 30)  # Clear screen with newlines
        
        if not self.started:
            print("Press ENTER to begin timing the prayer.\n\n")
            return
            
        print("Press ENTER for each syllable as you read.\n\n")
        
        # Display prayer with current syllable highlighted
        line = ""
        chars_in_line = 0
        
        for word_idx, syllables in enumerate(self.prayer_syllables):
            word = "".join(syllables)
            
            # Start a new line if current one is too long
            if chars_in_line + len(word) + 1 > 60:
                print(line)
                line = ""
                chars_in_line = 0
            
            # Format the current word/syllable
            if word_idx == self.current_word:
                # Split the word into before, current, and after syllables
                before = "".join(syllables[:self.current_syllable])
                current = syllables[self.current_syllable] if self.current_syllable < len(syllables) else ""
                after = "".join(syllables[self.current_syllable + 1:])
                
                formatted_word = before + "**" + current + "**" + after
            else:
                formatted_word = word
            
            line += formatted_word + " "
            chars_in_line += len(word) + 1
        
        # Print any remaining words
        if line:
            print(line + "\n")

    def run(self):
        """Main loop to run the timer."""
        try:
            while True:
                self.display_prayer()
                input()  # Wait for Enter key
                
                if not self.started:
                    self.started = True
                    self.last_press = time.time()
                    continue
                
                current_time = time.time()
                if self.last_press is not None:
                    time_diff = current_time - self.last_press
                else:
                    time_diff = 0.0
                rounded_diff = round(time_diff * 100) / 100
                self.syllable_times.append(rounded_diff)
                
                # Update timing and position
                self.last_press = current_time
                
                # Move to next syllable or word
                syllables_in_current_word = len(self.prayer_syllables[self.current_word])
                
                if self.current_syllable < syllables_in_current_word - 1:
                    self.current_syllable += 1
                else:
                    # Word is complete, calculate total word time
                    word_time = sum(self.syllable_times[-syllables_in_current_word:])
                    self.word_times.append(word_time)
                    
                    # Move to next word
                    self.current_word += 1
                    self.current_syllable = 0
                    
                    # Check if we're done
                    if self.current_word >= len(self.prayer_syllables):
                        break
            
            # Show final display of prayer
            print("\n" * 30)
            print("Prayer complete!\n")
            
            # Show final results
            print("\nTiming Results:\n")
            for i, t in enumerate(self.word_times):
                print(f"    v_delays[{i}] = {t:0.2f}     # {self.full_words[i]}")
                
        except KeyboardInterrupt:
            print("\nTimer stopped.")
            if self.word_times:
                print("\nTiming Results:\n")
                for i, t in enumerate(self.word_times):
                    print(f"    v_delays[{i}] = {t:0.2f}     # {self.full_words[i]}")

if __name__ == "__main__":
    app = TelnetPrayerTimer()
    app.run()