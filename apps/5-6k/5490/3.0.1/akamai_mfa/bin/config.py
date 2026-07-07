import logging

from baseconfig import AkamaiMfaConfig

LOG = logging.getLogger(__name__)

def main():
    print("Get or Set Akamai MFA configuration.")
    while True:
        action = input("\nEnter 'get', 'set', or 'exit': ").strip().lower()

        if action == 'get':
            config = AkamaiMfaConfig.load_from_file()
            print("\nCurrent configuration:")
            print(config.to_pretty_json())

        elif action == 'set':
            app_id = input("  Akamai MFA Integration Id: ").strip()
            signing_key = input("  Akamai MFA Signing Key: ").strip()
            host = input("  Akamai MFA Url: ").strip()

            if not app_id or not signing_key or not host:
                print("\nApp Id, Signing Key and Host are required. Please try again.")
                continue

            config = AkamaiMfaConfig(app_id, signing_key, host)
            config.save_to_file()
            print("\nConfiguration updated.")

        elif action == 'exit':
            print("\nExiting.")
            break

        else:
            print("\nInvalid command. Please enter 'get', 'set', or 'exit'.")


if __name__ == "__main__":
    main()
