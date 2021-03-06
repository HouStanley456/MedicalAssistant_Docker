# # -*- coding: utf-8 -*-
"""已訓練好模型predict.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1eIYWIU3w-xW6BDK2wA3f0Sy9vOwSTh-S

**開GPU!!!**
"""
# !nvidia-smi
# from google.colab import drive
# drive.mount('/content/drive')

import os
import torch
import pickle
from transformers import BertConfig, BertForSequenceClassification, BertTokenizer

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

modelversion = "model1"

filepath = os.path.join(os.path.abspath(os.path.dirname(__file__)), modelversion)
modelpath = os.path.join(filepath, "data_features.pkl")
config_file_path = os.path.join(filepath,  "config.json")
model_file_path  = os.path.join(filepath, "pytorch_model.bin")


def use_model(model_name, config_file_path, model_file_path, vocab_file_path, num_labels):
    # 選擇模型並加載設定
    if(model_name == 'bert'):
        from transformers import BertConfig, BertForSequenceClassification, BertTokenizer
        model_config, model_class, model_tokenizer = (BertConfig, BertForSequenceClassification, BertTokenizer)
        config = model_config.from_pretrained(config_file_path,num_labels = num_labels)
        model = model_class.from_pretrained(model_file_path, from_tf=bool('.ckpt' in 'bert-base-chinese'), config=config)
        # tokenizer
        tokenizer = BertTokenizer.from_pretrained(vocab_file_path, use_fast=True)
        return model, tokenizer
    elif(model_name == 'albert'):
        from albert.albert_zh import AlbertConfig, AlbertTokenizer, AlbertForSequenceClassification
        model_config, model_class, model_tokenizer = (AlbertConfig, AlbertForSequenceClassification, AlbertTokenizer)
        config = model_config.from_pretrained(config_file_path,num_labels = num_labels)
        model = model_class.from_pretrained(model_file_path, config=config)
        tokenizer = model_tokenizer.from_pretrained(vocab_file_path)
        return model, tokenizer

def compute_accuracy(y_pred, y_target):
    # 計算正確率
    _, y_pred_indices = y_pred.max(dim=1)
    n_correct = torch.eq(y_pred_indices, y_target).sum().item()
    return n_correct / len(y_pred_indices) * 100

def to_bert_ids(tokenizer,q_input):
    # 將文字輸入轉換成對應的id編號
    return tokenizer.build_inputs_with_special_tokens(tokenizer.convert_tokens_to_ids(tokenizer.tokenize(q_input)))

class DataDic(object):
    def __init__(self, answers):
        self.answers = answers #全部答案(含重複)
        self.answers_norepeat = sorted(list(set(answers))) # 不重複
        self.answers_types = len(self.answers_norepeat) # 總共多少類
        self.ans_list = [] # 用於查找id或是text的list
        self._make_dic() # 製作字典
    
    def _make_dic(self):
        for index_a,a in enumerate(self.answers_norepeat):
            if a != None:
                self.ans_list.append((index_a,a))

    def to_id(self,text):
        for ans_id,ans_text in self.ans_list:
            if text == ans_text:
                return ans_id

    def to_text(self,id):
        for ans_id,ans_text in self.ans_list:
            if id == ans_id:
                return ans_text

    @property
    def types(self):
        return self.answers_types
    
    @property
    def data(self):
        return self.answers

    def __len__(self):
        return len(self.answers)

def convert_data_to_feature(tokenizer, train_data_path):
    with open(train_data_path,'r',encoding='utf-8') as f:
        data = f.read()
    qa_pairs = data.split(r"\n")

    questions = []
    answers = []
    for qa_pair in qa_pairs:
        qa_pair = qa_pair.split()
        try:
            a,q = qa_pair
            questions.append(q)
            answers.append(a)
        except:
            continue
    
    assert len(answers) == len(questions)
    
    ans_dic = DataDic(answers)
    question_dic = DataDic(questions)

    q_tokens = []
    max_seq_len = 0
    for q in question_dic.data:
        bert_ids = to_bert_ids(tokenizer,q)
        if(len(bert_ids)>max_seq_len):
            max_seq_len = len(bert_ids)
        q_tokens.append(bert_ids)

    print("最長問句長度:",max_seq_len)
    assert max_seq_len <= 512 # 小於BERT-base長度限制

    # 補齊長度
    for q in q_tokens:
        while len(q)<max_seq_len:
            q.append(0)
    
    a_labels = []
    for a in ans_dic.data:
        a_labels.append(ans_dic.to_id(a))
    
    # BERT input embedding
    answer_lables = a_labels
    input_ids = q_tokens
    input_masks = [[1]*max_seq_len for i in range(len(question_dic))]
    input_segment_ids = [[0]*max_seq_len for i in range(len(question_dic))]
    assert len(input_ids) == len(question_dic) and len(input_ids) == len(input_masks) and len(input_ids) == len(input_segment_ids)

    data_features = {'input_ids':input_ids,
                    'input_masks':input_masks,
                    'input_segment_ids':input_segment_ids,
                    'answer_lables':answer_lables,
                    'question_dic':question_dic,
                    'answer_dic':ans_dic}
    
    output = open(modelpath , 'wb')
    pickle.dump(data_features,output)
    return data_features


    # load and init

def predicttext(inputs):
    pkl_file = open(modelpath, 'rb')
    data_features = pickle.load(pkl_file)
    answer_dic = data_features['answer_dic']
    # BERT
    model_setting = {
        "model_name":"bert", 
        "config_file_path": config_file_path,
        "model_file_path": model_file_path,
        "vocab_file_path":"bert-base-chinese", 
        "num_labels":24  # 分幾類 
    }    


    model, tokenizer = use_model(**model_setting)
    model.eval()

    q_inputs= [inputs]
    for q_input in q_inputs:
        bert_ids = to_bert_ids(tokenizer,q_input)
        assert len(bert_ids) <= 512
        input_ids = torch.LongTensor(bert_ids).unsqueeze(0)


        # predict
        outputs = model(input_ids)
        predicts = outputs[:2]
        predicts = predicts[0]
        max_val = torch.max(predicts)
        label = (predicts == max_val).nonzero().numpy()[0][1]
        
        ans_label = answer_dic.to_text(label)
        
    
    return(str(ans_label))

if __name__ == "__main__":    
    print(predicttext("123"))
    pass