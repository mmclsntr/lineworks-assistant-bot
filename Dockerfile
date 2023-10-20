FROM public.ecr.aws/sam/build-python3.9:1.52.0-arm64

# update
RUN yum update -y
RUN  yum -y install yum-utils

# Install Nodejs
RUN yum install https://rpm.nodesource.com/pub_16.x/nodistro/repo/nodesource-release-nodistro-1.noarch.rpm -y
RUN yum install nodejs -y --setopt=nodesource-nodejs.module_hotfixes=1

RUN pip install boto3

# install serverless framework
RUN npm install -g serverless

# work directory
WORKDIR /app
COPY . .

RUN pip install -r requirements.txt
RUN npm install
