import os
import email
import imaplib
import argparse
from mailbox import mbox

# Function for converting downloaded mailboxes from EML to Mbox format
def convert_to_mbox(mailbox_folder):
    for item in os.listdir(mailbox_folder):
        item_path = os.path.join(mailbox_folder, item)
        if os.path.isdir(item_path):
            # Recursively convert nested mailboxes
            convert_to_mbox(item_path)
        elif item.endswith('.eml'):
            mbox_path = os.path.join(mailbox_folder, f'{os.path.basename(os.path.normpath(mailbox_folder))}.mbox')
            mbox_file = mbox(mbox_path)
            with open(item_path, 'rb') as f:
                message = f.read()
            mbox_file.add(message)
            mbox_file.flush()

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Download all mailboxes and their contents from a Yandex email account')
    parser.add_argument('username', type=str, help='Yandex email account username')
    parser.add_argument('password', type=str, help='Yandex email account password')
    parser.add_argument('--mbox', action='store_true', help='Convert downloaded mailboxes to Mbox format')
    args = parser.parse_args()

    # Connect to the Yandex IMAP server over SSL
    imap_server = 'imap.yandex.com'
    imap_port = 993
    print(f'Connecting to {imap_server}:{imap_port}...')
    connection = imaplib.IMAP4_SSL(imap_server, imap_port)

    # Login to the Yandex email account
    print(f'Logging in as {args.username}..')
    try:
        connection.login(args.username, args.password)
    except Exception as e:
        print('Error: Failed to login to the Yandex email account')
        print(str(e))
        exit()

    # Get the list of mailboxes
    print('Listing account mailboxes..')
    try:
        connection.select()
        typ, data = connection.list()
    except Exception as e:
        print('Error: Failed to get the list of mailboxes')
        print(str(e))
        exit()

    # Create local account folder
    local_folder_name = args.username
    os.makedirs(local_folder_name, exist_ok=True)

    # Download all mailboxes and their contents locally
    for mailbox in data:
        # Mailbox name
        mailbox_name = mailbox.decode('utf-8').split(' "|" ')[-1].replace('"', '').replace('/', '_')
        mailbox_name_canonical = mailbox_name.replace('|', '/')

        # Mailbox server path
        mailbox_path = mailbox_name.split('|')

        # Determine local mailbox folder path
        mailbox_folder_path = local_folder_name
        for folder in mailbox_path:
            mailbox_folder_path = os.path.join(mailbox_folder_path, folder)

        # Create necessary directories recursively
        os.makedirs(mailbox_folder_path, exist_ok=True)

        # Select mailbox
        try:
            connection.select(mailbox_name)
            typ, data = connection.search(None, 'ALL')
        except Exception as e:
            print(f'Error: Failed to select mailbox {mailbox_name_canonical}')
            print(str(e))
            continue

        # Download mailbox contents
        print(f'Downloading contents of mailbox {mailbox_name_canonical}..')
        for email_id in data[0].split():
            try:
                typ, data = connection.fetch(email_id, '(RFC822)')
                email_content = data[0][1]

                # Parse the email message
                msg = email.message_from_bytes(email_content)

                # Save the email message in EML format
                encoding = msg.get_content_charset() or 'utf-8'
                with open(os.path.join(mailbox_folder_path, f'{email_id.decode()}.eml'), 'wb') as f:
                    f.write(email_content)
            except Exception as e:
                print(f'Error: Failed to download email {email_id.decode()} from mailbox {mailbox_name_canonical}')
                print(str(e))
                continue

        if args.mbox:
            convert_to_mbox(mailbox_folder_path)

    # Close the connection to the Yandex email account
    print('Closing the connection..')
    try:
        connection.close()
        connection.logout()
    except Exception as e:
        print('Error: Failed to close the connection to the Yandex email account')
        print(str(e))
        exit()

    print('All mailboxes and their contents have been downloaded successfully!')