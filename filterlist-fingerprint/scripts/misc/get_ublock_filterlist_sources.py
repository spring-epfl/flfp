import requests


def get_url(asset):
    
    if "cdnURLs" in asset:
        return asset["cdnURLs"][0]
    
    if "contentURL" in asset:
        if isinstance(asset["contentURL"], list):
            
            # find the one with https
            for url in asset["contentURL"]:
                if url.startswith("https"):
                    return url
        
        else:
            return asset["contentURL"]
        
        raise ValueError(f"Could not find a valid URL for asset: {asset}")
    

if __name__ == "__main__":
    
    file_url = "https://raw.githubusercontent.com/gorhill/uBlock/1ce845b2dc4c7fad5e74b76d6f407897e637f4c5/assets/assets.json"
    
    resp = requests.get(file_url)
    
    if resp.status_code != 200:
        raise ValueError(f"Failed to download file: {file_url}")
    
    assets = resp.json()
    
    del assets['assets.json']
    del assets['public_suffix_list.dat']
    
    for asset in assets:
        print(f"""
            - name: {asset}
              aliases: [{assets[asset].get('title', "")}]
              url: {get_url(assets[asset])}
              """)
        
