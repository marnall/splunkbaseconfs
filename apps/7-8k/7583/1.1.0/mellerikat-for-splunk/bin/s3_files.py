import boto3
from botocore.exceptions import ClientError
import os

class S3Files:
    def __init__(self, profile_name):
        if(len(profile_name)>0): 
            session = boto3.Session(profile_name=profile_name)
            self.s3_client = session.client('s3')
        else:
            self.s3_client = boto3.client('s3')


    def getBucketList(self, Bucket, Prefix=None):
        if Prefix is None:
            Prefix  = 'test_splunk/'
        response  = self.s3_client.list_objects_v2(
            Bucket=Bucket,
            Prefix=Prefix)
        return response


    def getList(self, Bucket, Prefix=None):

        if Prefix is None:
            Prefix = 'test_splunk/'
        response = self.s3_client.list_objects_v2(
            Bucket=Bucket,
            Prefix=Prefix)

        object_sizes = {}
        
        for obj in response['Contents']:
            key = obj['Key']
            size = obj['Size']
            last_modified = obj['LastModified'].isoformat()
            object_sizes[key] = {'size': size, 'last_modified': last_modified}
        
        return object_sizes        



    def uploadFile(self, file_name, Bucket, object_name=None):
        """ S3 버킷에 파일을 업로드합니다.
        
        :param file_name: 업로드할 파일
        :param Bucket: 업로드될 버킷
        :param object_name: S3 객체이름. 없으면 file_name 사용
        :return: 파일이 업로드되면 True, 아니면 False
        """
        
        # S3 객체이름이 정의되지 않으면, file_name을 사용
        if object_name is None:
            object_name = os.path.basename(file_name)
        
        # 파일 업로드
        try:
            resposne = self.s3_client.upload_file(file_name, Bucket, object_name)

            response = self.s3_client.head_object(Bucket=Bucket, Key=object_name)
            # last_modified = response['LastModified']

            # UTC 시간대의 datetime 객체로 변환
            # last_modified_utc = last_modified.astimezone(timezone.utc)
            return response

        except ClientError as e:
            # logging.error(e)
            # raise S3UploadFailedError (
            None
        return None


    def deleteFile(self, Bucket, object_name=None):
       
        # 파일 삭제
        # s3_client = boto3.client('s3')
        # session = boto3.Session(profile_name="mellerikat")
        # session = boto3.Session()
        # s3_client = session.client('s3')
        # s3_client = boto3.client('s3')
        self.s3_client.delete_object(Bucket = Bucket, Key = object_name)

