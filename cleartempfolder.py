import os

def clearTempFolder(tempfolder):
        try:
            for item in os.listdir(tempfolder):
                item_path = os.path.join(tempfolder, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
            print(f"Folder {tempfolder} Cleared")
        except Exception as e:
            print(f"Error occurred: {e}")

if __name__ == "__main__":
     clearTempFolder("/Users/ryanjewett/Documents/CPE4850/SAVE_HERE")