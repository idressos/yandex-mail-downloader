import os
import email
import imaplib
import argparse
from mailbox import mbox
from datetime import datetime, timedelta

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
    parser.add_argument('-m', '--mbox', action='store_true', help='Convert downloaded mailboxes to Mbox format')
    parser.add_argument('-s', '--sync', action='store_true', help='Delete local email files that are not on the server')
    parser.add_argument('-a', '--max-age', type=int, default=-1, help='Only download emails newer than (since) X days')
    parser.add_argument('-e', '--exclude', type=str, nargs='+', help='List mailboxes to exclude from downloading')
    parser.add_argument('-i', '--include', type=str, nargs='+', help='List mailboxes to include (only those specified will be downloaded)')

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
    print('Listing account mailboxes..\n')
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

        if args.include is not None and mailbox_name_canonical not in args.include:
            continue
        if args.exclude is not None and mailbox_name_canonical in args.exclude:
            continue

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
            connection.select('"' + mailbox_name + '"' if (' ' in mailbox_name or not mailbox_name.isascii()) else mailbox_name, readonly=True)

            if(args.max_age > 0):
                cutoff_date = (datetime.today() - timedelta(days=args.max_age)).strftime('%d-%b-%Y')
                typ, data = connection.uid('SEARCH', None, f'SINCE {cutoff_date}')
            else:
                typ, data = connection.uid('SEARCH', None, 'ALL')
        except Exception as e:
            print(f'Error: Failed to select mailbox {mailbox_name_canonical}')
            print(str(e))
            continue

        # Initialize counters
        saved = 0
        skipped = 0
        failed = 0
        removed = 0
        total = 0

        # Download mailbox contents
        print(f'Downloading contents of mailbox {mailbox_name_canonical}..')

        email_uids = data[0].split()

        for email_uid in email_uids:
            total += 1

            try:
                # Decode email UID
                email_uid = email_uid.decode()

                email_file_name = f'{email_uid}.eml'
                email_file_path = os.path.join(mailbox_folder_path, email_file_name)
                email_file_size = os.stat(email_file_path).st_size if os.path.isfile(email_file_path) else -1

                # Check if the email has already been downloaded
                if email_file_name in os.listdir(mailbox_folder_path) and email_file_size > 0:
                    skipped += 1
                    continue

                typ, data = connection.uid('FETCH', email_uid, '(RFC822)')
                email_content = data[0][1]

                # Parse the email message
                msg = email.message_from_bytes(email_content)

                # Save the email message in EML format
                encoding = msg.get_content_charset() or 'utf-8'
                with open(email_file_path, 'wb') as f:
                    f.write(email_content)
                    saved += 1
            except Exception as e:
                print(f'Error: Failed to download email with UID {email_uid} from mailbox {mailbox_name_canonical}')
                print(str(e))
                failed += 1
                continue

        if args.sync:
            for file in os.listdir(mailbox_folder_path):
                if file.endswith(".eml"):
                    email_uid = os.path.splitext(file)[0]
                    email_file_path = os.path.join(mailbox_folder_path, file)
                    if email_uid.encode() not in email_uids:
                        os.remove(email_file_path)
                        removed += 1

        print(f'  Saved: {saved}\n  Skipped: {skipped}\n  Failed: {failed}\n  Removed: {removed}\n  Total: {total}')

        # Convert to MBOX format if specified
        if args.mbox:
            print('Creating Mbox file..\n')
            convert_to_mbox(mailbox_folder_path)
        else:
            print('')

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