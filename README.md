# moneyforward-binance-sync

Application to sync balance from Binance to MoneyForward.

This application have two steps:

1. Fetch amount, price for each currency (including savings) via Binance API. Convert balance into JPY and calculate sum.

2. Open Selenium web browser, login to MoneyForward and update the account for Binance.

## Setup

### Packages

Add repository configuration.

```bash
sudo vi /etc/yum.repos.d/google-chrome.repo
```

Paste below & save.

```repo
[google-chrome]
name=google-chrome
baseurl=http://dl.google.com/linux/chrome/rpm/stable/$basearch
enabled=0
gpgcheck=1
gpgkey=https://dl-ssl.google.com/linux/linux_signing_key.pub
```

Install packages.

```bash
sudo yum update -y

sudo yum install python3 git -y
sudo yum install --enablerepo=google-chrome google-chrome-stable -y
google-chrome --version  # Google Chrome 94.0.4606.81

# Get Chromedriver for your Chrome version.
cd /home/ec2-user
wget https://chromedriver.storage.googleapis.com/94.0.4606.61/chromedriver_linux64.zip
unzip chromedriver_linux64.zip

# Install double byte character fonts for Chrome
sudo yum install ipa-gothic-fonts ipa-mincho-fonts ipa-pgothic-fonts ipa-pmincho-fonts -y

# clone repository & install requirements
git clone https://github.com/yota-p/moneyforward-binance-sync.git
cd moneyforward-binance-sync
pip3 install --user -r requirements.txt
cp ~/chromedriver ~/moneyforward-binance-sync
```

### Python

Use Python3 as default.

```bash
python -V  # Python 2.7.16 - current version

cd /usr/bin/
ls python*  # python, python2.7, python3.7, ...
sudo unlink ./python
sudo ln -s /usr/bin/python3.7 ./python

python -V  # Python 3.7.10 (new version)
```

Now if you run `yum`, it will cause `SyntaxError` since it includes Pyhon2.x specific syntax. To fix this, edit the first line of `/usr/bin/yum` and `/usr/libexec/urlgrabber-ext-down`.

```Python
# Before:
#!/usr/bin/python

# After:
#!/usr/bin/python2.7
```

### Credentials

Copy json templates from `secrets/template`. Fill your parameters and save them as `secrets/slackauth.json` and `secrets/config.json`. These files will be ignored from source control as specified in `.gitignore`.

## Run

```bash
python main.py
```

To run this every 5 minutes, hit `crontab -e` and create a job.

```cron
*/5 * * * * cd /home/ec2-user/fumotoppara-vacancy-checker; python main.py --production
```

## Tips

If Chromedriver exited before calling `driver.close()` or `driver.quit()`, it's process will remain and use up memory and cpu. If you with to cleanup, run

```bash
ps aux | grep chrome | grep -v grep | awk '{ print "kill -9", $2 }' | sh
```

Note that `driver.close()` only closes current window. Use `driver.quit()` to close Chromedriver handling multiple window.
