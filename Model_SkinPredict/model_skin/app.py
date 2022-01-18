from skinpredict import predict
from flask import Flask

app=Flask(__name__)
@app.route("/<path:image>", methods=['get'])
def predictskin(image):    
    output = predict(image)
    return output

if __name__=="__main__":
    app.run(host="0.0.0.0", port="5000")
