# ms-auth-to-mc-bearer
Simple code to gather Minecraft's Bearer token using a Xbox Live account's email and password

## this is meant to be a library not a piece of code to implement
Yea this is meant to just be put on a file and imported with a local import, let's say you put `oauth.py` in the same folder as `test.py` 
and the code that follows is of `test.py`:
```
from oauth import gather_mc_bearer

bearer_token = gather_mc_bearer("email@example.com", "Password")
print(bearer_token)
```
When executing it (if you put working credentials ofc) you will get the Minecraft Bearer token of that account which lasts for 24 hours.
## ??
I don't know why people should need this since it's literally Xbox's API Wrapper code with just some changes to the requests to make it work for Minecraft,
but if you need it feel free to use it 
