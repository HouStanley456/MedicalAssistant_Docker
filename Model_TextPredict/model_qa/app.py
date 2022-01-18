from textpredict import predicttext, DataDic
from flask import Flask

app=Flask(__name__)
@app.route("/<text>", methods=['get'])
def predict(text):
    output = predicttext(text)
    return output

if __name__=="__main__":
    app.run(host="0.0.0.0", port="5000")
