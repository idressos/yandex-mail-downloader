# :envelope_with_arrow: Yandex.Mail Downloader

This is a Python script that can download all the mailboxes and their contents from a Yandex.Mail account.  
It supports nested mailboxes, saves emails to EML and Mbox format, and includes email attachments. The script only requires Python3 to run.

## Usage

Before running the script, make sure you have generated an app password for IMAP through Yandex.  

To run the script, open your terminal and navigate to the directory where the script is located. Then run the following command, replacing `[username]` and `[password]` with your Yandex.Mail account username and app password for IMAP, respectively:

```
python3 yandex-mail-downloader.py [username] [password]
```

The script will start downloading all the mailboxes and their contents from your account.  
You can also choose to save the emails in Mbox format by supplying the `--mbox` flag, or only download emails newer than X days by using the --max-age parameter.
The script will automatically create a folder for each mailbox and save the emails inside it.