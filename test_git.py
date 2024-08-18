import os
os.chdir("../plant-watering-vlogs")
os.system("git pull")
os.system("git add .")
os.system("git commit -m'Adding data'")
os.system("git push")