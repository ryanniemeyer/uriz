uriz is a simple, non-production example of a URL shortener [Django](https://www.djangoproject.com/) site. The purpose of this project is to walk someone through the steps for deploying a simple web app utilizing the following [Amazon Web Services](http://aws.amazon.com/) (AWS) features:

* [EC2](http://aws.amazon.com/ec2/) for the web nodes
* [S3](http://aws.amazon.com/s3/) + [CloudFront](http://aws.amazon.com/cloudfront/) for static content
* [DynamoDB](http://aws.amazon.com/dynamodb/) for storage
* [Route53](http://aws.amazon.com/route53/) for DNS
* [ELB](http://aws.amazon.com/elasticloadbalancing/) to balance load to the EC2 web nodes

This tutorial assumes you've already created a [AWS](http://aws.amazon.com/) account.

## Setup Your URL Shortener Domain

The first step is obtaining a domain for your URL shortener from your favorite domain registrar (e.g. [Namecheap](http://namecheap.com/)). I picked uriz.in for this example, but you can simply fork this project and replace all occurrences of uriz.in with whatever your URL shortener domain is.

After you've registered your domain, create a [Route53](http://aws.amazon.com/route53/) hosted zone via the AWS console:

![Route53 in AWS Console](http://d283nftekqpxlr.cloudfront.net/img/github-pages/route53-1.png)
![Route53 new zone](http://d283nftekqpxlr.cloudfront.net/img/github-pages/route53-2.png)
![Route53 name servers](http://d283nftekqpxlr.cloudfront.net/img/github-pages/route53-3.png)

Then, change your domain's name servers to your [Route53](http://aws.amazon.com/route53/) hosted zone's name servers:

![Namecheap Custom Name Servers](http://d283nftekqpxlr.cloudfront.net/img/github-pages/namecheap-nameservers.png)

Note that it may take a while for the DNS changes to propagate, which is why I put this step first.

## Data Storage

Now that we've got our URL shortener domain and have it pointing to our Amazon DNS, let's set up our database. For this example we'll be using [DynamoDB](http://aws.amazon.com/dynamodb/), Amazon's high performance, scalable and reliable key-value store.

We'll have one table where our short URL tokens are the primary key and the value has metadata including the long URL, when the URL was first shortened and a count of how many times the short URL is visited. We'll also have a table that serves as a reverse index where the long URL is the primary key. There are certainly better ways to implement a URL shortener, but I'm not trying to demonstrate a bit.ly killer here, so bear with me.

You can use the [DynamoDB APIs](http://aws.amazon.com/documentation/dynamodb/) or your favorite [AWS](http://aws.amazon.com/) client SDK to add/remove/edit your tables, but for this example we'll use the web console to create these two tables (uriz and uriz_long):

![DynamoDB Console](http://d283nftekqpxlr.cloudfront.net/img/github-pages/dynamo-1a.png)
![DynamoDB Add uriz Table](http://d283nftekqpxlr.cloudfront.net/img/github-pages/dynamo-2.png)
![DynamoDB Accept Defaults 1](http://d283nftekqpxlr.cloudfront.net/img/github-pages/dynamo-3.png)
![DynamoDB Accept Defaults 2](http://d283nftekqpxlr.cloudfront.net/img/github-pages/dynamo-4.png)
![DynamoDB Table Created](http://d283nftekqpxlr.cloudfront.net/img/github-pages/dynamo-5.png)
![DynamoDB Add uriz_long Table](http://d283nftekqpxlr.cloudfront.net/img/github-pages/dynamo-6.png)
![DynamoDB Both Tables Created](http://d283nftekqpxlr.cloudfront.net/img/github-pages/dynamo-7.png)

## Static Content

Before we deploy our code, let's get our static content into [S3](http://aws.amazon.com/s3/) and have it served up via Amazon's [CDN](http://en.wikipedia.org/wiki/Content_delivery_network) ([CloudFront](http://aws.amazon.com/cloudfront/)). In this example I simply have a single versioned CSS file. Probably the most amazing CSS anyone has ever or will ever create, I might add.

Checkout or clone this project (or your fork of this project) to your local machine. You'll need the project checked out to upload the s-1.css file in the uriz/static/css directory to [S3](http://aws.amazon.com/s3/) and later to run the command that deploys to your web nodes.

After you get the code on your machine, go back to the AWS console and find the S3 service. Create a bucket with a css folder and upload s-1.css into it:

![S3 Console](http://d283nftekqpxlr.cloudfront.net/img/github-pages/s3-1.png)
![S3 New Bucket](http://d283nftekqpxlr.cloudfront.net/img/github-pages/s3-2.png)
![S3 css Folder](http://d283nftekqpxlr.cloudfront.net/img/github-pages/s3-3.png)
![S3 Upload CSS File](http://d283nftekqpxlr.cloudfront.net/img/github-pages/s3-4.png)

Be sure to mark the css folder and the s-1.css file as public via the Actions drop down menu.

Now locate CloudFront in the AWS console. Create a distribution on top of that S3 bucket so your CSS is served as close to your user as possible:

![CloudFront console](http://d283nftekqpxlr.cloudfront.net/img/github-pages/cloudfront-1.png)
![CloudFront Add Distribution](http://d283nftekqpxlr.cloudfront.net/img/github-pages/cloudfront-2.png)
![CloudFront Caching](http://d283nftekqpxlr.cloudfront.net/img/github-pages/cloudfront-3.png)
![CloudFront Confirm](http://d283nftekqpxlr.cloudfront.net/img/github-pages/cloudfront-4.png)
![CloudFront Deployed](http://d283nftekqpxlr.cloudfront.net/img/github-pages/cloudfront-5.png)

In a production setting you'd want to automate the process of pushing your static content to [S3](http://aws.amazon.com/s3/), probably also doing things like compiling LESS/SASS, minifying, etc, but I'll leave that exercise to the reader. 

## Deploy the Code!

Ok, we've got our [DynamoDB](http://aws.amazon.com/dynamodb/) tables out there, our static content served up via CloudFront and our domain is pointed to Amazon's DNS. Now let's deploy the uriz Django app to [EC2](http://aws.amazon.com/ec2/).

First thing we'll do is create a KeyPair that will allow us to SSH to our machine. This lets us deploy the code and log into the box should things go wrong. In the EC2 web console, go to the "Key Pairs" page and create a new pair. Name it uriz or something similar. When it downloads, save it to your local machine in the path /ec2/accounts/uriz/uriz.pem (if you want to save it somewhere else, you'll need to change that path in uriz/fabfile.py mentioned below).

Next, we'll define a security group for our web nodes that tells each box to only open port 22 (SSH) and port 80 (HTTP). Do that via the "Security Groups" page in the EC2 console, making sure to click the Apply Changes button when you're done:

![Security Groups](http://d283nftekqpxlr.cloudfront.net/img/github-pages/securitygroup-1.png)
![Add Security Group](http://d283nftekqpxlr.cloudfront.net/img/github-pages/securitygroup-2.png)
![Open Ports 22 and 80 in Security Group](http://d283nftekqpxlr.cloudfront.net/img/github-pages/securitygroup-3.png)

We're ready to launch a new machine in the cloud. In this example I'm using a bare bones Ubuntu 12.04, 64-bit instance storage Amazon Machine Image (AMI) ami-3c994355. Let's launch a single box using the KeyPair and security group we just set up:

![EC2 Console](http://d283nftekqpxlr.cloudfront.net/img/github-pages/ec2-1.png)
![EC2 Classic](http://d283nftekqpxlr.cloudfront.net/img/github-pages/ec2-2.png)
![EC2 Choose AMI](http://d283nftekqpxlr.cloudfront.net/img/github-pages/ec2-3.png)
![EC2 Choose Zone](http://d283nftekqpxlr.cloudfront.net/img/github-pages/ec2-4.png)
![EC2 Take Defaults](http://d283nftekqpxlr.cloudfront.net/img/github-pages/ec2-5.png)
![EC2 Choose Name](http://d283nftekqpxlr.cloudfront.net/img/github-pages/ec2-6.png)
![EC2 Choose KeyPair](http://d283nftekqpxlr.cloudfront.net/img/github-pages/ec2-7.png)
![EC2 Choose Security Group](http://d283nftekqpxlr.cloudfront.net/img/github-pages/ec2-8.png)
![EC2 Confirm](http://d283nftekqpxlr.cloudfront.net/img/github-pages/ec2-9.png)
![EC2 Launched](http://d283nftekqpxlr.cloudfront.net/img/github-pages/ec2-10.png)

Sweet! We've got an Ubuntu 12.04 small instance running! Make note of your new instance's Public DNS address, as you'll need to know that to deploy the code.

Now let's install everything our Django app needs to run. To do that, we're using [fabric](http://fabfile.org/), which is a really nice Python library for running SSH commands on remote or local hosts.

To run the fabric command to deploy uriz to your new [EC2](http://aws.amazon.com/ec2/) instance, you'll need a local Python environment that has fabric installed. In general, this means follow the instructions you'll find all over the interwebs that walk you through:

1. Installing Python 2.7
2. Installing easy_install
3. easy_install pip
4. pip install virtualenv
5. pip install virtualenvwrapper
6. mkvirtualenv uriz
7. workon uriz
8. pip install fabric

Isn't Python packaging great? Hopefully things get much easier in Python 3.3+, but I digress.

One more thing we need to do before deploying the code is enter your Amazon account's access key/secret so the app can read and write to [DynamoDB](http://aws.amazon.com/dynamodb/). You can retrieve your key/secret from your [AWS](http://aws.amazon.com/) account's "Security Credentials" link, which is in the drop down in the upper right of most AWS console pages. After locating your key and secret, add a file to your local clone/fork of the uriz project inside of the uriz app named my_aws_settings.py. In my_aws_settings.py you'll need to define two variables, which should look something like this:

    AWS_ACCESS_KEY_ID = 'BZEDKIEFHLYIHZDQTQKB'
    AWS_SECRET_ACCESS_KEY = 'FazbumeFuCCA14ED7ahBtd/evqyGSWCtwcugF7vJ'

The fabfile will use those variables to write a similar file to your deployed uriz web apps.

(Don't worry, that isn't my actual key/secret and I've added my_aws_settings.py to this project's .gitingore, so it will only be on your local machine, not checked into github.)

Alright, now let's setup our new [EC2](http://aws.amazon.com/ec2/) boxes by running the newbox fabric command, passing in your instance's Public DNS address in the -H argument:

    $ workon uriz
    $ cd ~/uriz
    $ fab -H ec2-50-17-41-254.compute-1.amazonaws.com newbox
    
This command may take a few minutes to run, most of the time spent updating the OS and installing packages. After it's done, let's see if it worked.

We haven't told the DNS ([Route53](http://aws.amazon.com/route53/)) about this new box yet, but we can hit it directly via the public IP. Visit that in your browser, e.g. http://50.17.41.254/ if your instance's Public DNS address was ec2-50-17-41-254.compute-1.amazonaws.com. If everything went well you should see a state-of-the-art URL shortener that looks something like this:

![uriz on instance ip](http://d283nftekqpxlr.cloudfront.net/img/github-pages/uriz-direct-to-host.png)

Hitting the box directly works, but you obviously don't want to send users to that single machine's ip address, so let's point our domain's DNS to our [EC2](http://aws.amazon.com/ec2/) instance(s). What we want to do here is use Amazon's [Elastic Load Balancer (ELB)](http://aws.amazon.com/elasticloadbalancing/) so we can easily add and remove web nodes from our running website to handle changes in traffic and no-downtime upgrades and technology changes.

Creating a load balancer is fairly straight forward in the EC2 console:

![ELB Console](http://d283nftekqpxlr.cloudfront.net/img/github-pages/elb-1.png)
![ELB New](http://d283nftekqpxlr.cloudfront.net/img/github-pages/elb-2.png)
![ELB Healthcheck](http://d283nftekqpxlr.cloudfront.net/img/github-pages/elb-3.png)
![ELB Instances](http://d283nftekqpxlr.cloudfront.net/img/github-pages/elb-4.png)
![ELB Confirm](http://d283nftekqpxlr.cloudfront.net/img/github-pages/elb-5.png)
![ELB Status](http://d283nftekqpxlr.cloudfront.net/img/github-pages/elb-6.png)

Now that our load balancer is created and our instance is "In Service", let's add this load balancer to our DNS so traffic for our domain starts hitting the [ELB](http://aws.amazon.com/elasticloadbalancing/). We'll point both the naked domain (uriz.in) and the www subdomain (www.uriz.in) to our load balancer:

![Route53 console](http://d283nftekqpxlr.cloudfront.net/img/github-pages/route53-4.png)
![Route53 naked domain](http://d283nftekqpxlr.cloudfront.net/img/github-pages/route53-5.png)
![Route53 www subdomain](http://d283nftekqpxlr.cloudfront.net/img/github-pages/route53-6.png)
![Route53 domain](http://d283nftekqpxlr.cloudfront.net/img/github-pages/route53-7.png)

After those changes, try hitting your URL shortener domain in your browser. It should work:

![uriz.in homepage](http://d283nftekqpxlr.cloudfront.net/img/github-pages/uriz-in-1.png)
![uriz.in short url info page](http://d283nftekqpxlr.cloudfront.net/img/github-pages/uriz-in-2.png)

Sweet. We've got [Route53](http://aws.amazon.com/route53/)->[ELB](http://aws.amazon.com/elasticloadbalancing/)->[EC2](http://aws.amazon.com/ec2/)+[DynamoDB](http://aws.amazon.com/dynamodb/)+[CloudFront](http://aws.amazon.com/cloudfront/) working. Our load balancer is only pointing to a single web node, which isn't cool because machines go down, especially boxes "in the cloud". Plus, this is the best URL shortener anyone has ever produced, so it's highly likely to go viral when Justin Bieber catches wind of it. We've got to be ready for his tweets!

Follow the steps above to create another [EC2](http://aws.amazon.com/ec2/) instance and run the newbox fabric command on your new box's host. After your new box is up and running, go back to the Load Balancers section of the [EC2](http://aws.amazon.com/ec2/) console and add your new box to your existing load balancer. It should now be very easy to add/remove as many web nodes as you need.

## Wrapping Up

Now you're probably not going to survive a Bieber tweet with two small web nodes, but you're well on your way. The next move is creating AMIs and taking advantage of some of the [AWS](http://aws.amazon.com/) auto scaling features. That's a bit advanced and can be tricky depending on what all you have in your stack, so I'll leave that to another example project for another day.

That's it! Not quite [Heroku](http://www.heroku.com/) or [App Engine](https://developers.google.com/appengine/) simple, but the trade off for the additional complexity is more control over the technologies you can use to construct your app. I'm a huge fan of [AWS](http://aws.amazon.com/) and I hope this helps someone out there get started with some of these services.

O yeah, one more thing... Don't forget to shut down your EC2 instances if you're no longer needing them! Chances are http://uriz.in/ won't be up when you read this :)