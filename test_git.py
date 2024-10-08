from git import Repo

PATH_OF_GIT_REPO = r'/home/loido/git_repositories/plant-watering-vlogs/.git'  # make sure .git folder is properly configured
COMMIT_MESSAGE = 'Adding vlogs'

def git_push():
    try:
        repo = Repo(PATH_OF_GIT_REPO)
        repo.git.add(".")
        repo.index.commit(COMMIT_MESSAGE)
        origin = repo.remote(name='origin')
        origin.push()
    except:
        print('Some error occured while pushing the code') 

git_push()