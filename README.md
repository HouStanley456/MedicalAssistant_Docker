資料夾內容：

     MedicalAssistant_app : Line程式碼
     Model_SkinPredict : 皮膚模型
     Model_TextPredict : 文字模型
     
筆記區：
     
     馬達地端架設
     https://hackmd.io/e4G0PoXoREu9ZG4yTv9xvw?view#%E5%B0%88%E6%A1%88
     楊老闆Uwsgi
     https://hackmd.io/@T-pTTDjuS7-wiigIYk3eRw/Hkgk7pM6t
     秉之Docker架設
     https://github.com/HouStanley456/Docker-Mysql
     

部署至Cloud Run：

      建立Docker container and Image
      
      step1 使用 ./base 中的Dockerfile
            cd /base
            sudo docker build -t medical_docker .
            
      step2 使用 Image 建立 container 
            sudo docker run -d --rm -p 8888:8888 medical_docker 
            
      step3 確定 docker container 可以正常運行 Flask
            curl 127.0.0.1:8888/after
            *測試能否連到Flask
            
      step4 將 Image 部署到 Container Registry
            * https://blog.cloud-ace.tw/application-modernization/serverless/cloud-run-api-server/
            sudo gcloud init
            sudo gcloud builds submit --tag gcr.io/{project_id}/{docker_name}
      step5 部署到 Cloud Run 
            sudo gcloud run deploy --image gcr.io/{project_id}/{docker_name} \
            --platform managed \
            --port 8888 \
            --memory 4Gi \
            --timeout=6m \
     
     ＊＊要注意port的問題＊＊
     
     


-------------------------------------------------------------------
資料閱讀區：

Container Registry
      
      https://ithelp.ithome.com.tw/articles/10220807
      https://blog.cloud-ace.tw/application-modernization/serverless/cloud-run-api-server/
