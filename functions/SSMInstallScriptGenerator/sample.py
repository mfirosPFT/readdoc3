# ask input from user for tenant name
# use the input and call onboard tenant API to get activationID and activationCode as response
# download amazon-ssm-agent.deb and install it using dpkg -i amazon-ssm-agent.deb
# stop the service amazon-ssm-agent stop
# use the activationID and activationCode to register the tenant by running sudo -E amazon-ssm-agent -register -code $code -id $id -region $region
# start the service amazon-ssm-agent start
# create cloudwatch alarms using api call
# collect hostname, ip and use storage.json from local directory to store the data and call api to store the data
# exit the script

import json
import os
import sys
import time
import subprocess
import logging
import argparse
from subprocess import Popen, PIPE


def prRed(prt):
    print("\033[91m {}\033[00m".format(prt))


def prGreen(prt):
    print("\033[92m {}\033[00m".format(prt))


def prYellowC(prt):
    print("\033[93m {}\033[00m".format(prt))


def prYellow(prt):
    print("\33[5m {}\033[00m".format(prt))


def get_args():
    parser = argparse.ArgumentParser(description="Process tenant name")
    parser.add_argument("-t", "--tenant", help="tenant name", required=True)
    args = parser.parse_args()
    return args


def get_activation_details(theater_id, os_name, theater_name):
    prYellow("Getting activation details")
    import requests

    url = "{{ ONBOARD_TENANT_URL }}"
    # url = "https://pq5ymlotdc.execute-api.ap-south-1.amazonaws.com/Prod/ssmactivation"
    payload = {"theater_id": theater_id,
               "os": os_name, "theater_name": theater_name}
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        prGreen("Successfully got activation details")
        print(response.json())
        return response.json()
    else:
        prRed("Error: {}".format(response.json()))
        sys.exit(1)


def install_ssm_agent(activation_details, theater_id, theater_name, theater_email):
    prYellow("Starting installation of ssm agent")
    import requests

    activation_id = activation_details["ActivationId"]
    activation_code = activation_details["ActivationCode"]
    region = activation_details["Region"]
    # check if os is linux or windows and download the ssm agent accordingly
    if os.name == "posix":
        prYellow("Downloading ssm agent for linux")
        subprocess.call(
            [
                "wget",
                "https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/debian_amd64/amazon-ssm-agent.deb",
            ]
        )
        subprocess.call(["sudo", "dpkg", "-i", "amazon-ssm-agent.deb"])
        prGreen("Successfully downloaded ssm agent")
        # install the package
        prYellow("Installing ssm agent")

        subprocess.call(["sudo", "dpkg", "-i", "amazon-ssm-agent.deb"])
        prGreen("Successfully installed ssm agent")
        stop_ssm_agent()
        # get hostname
        hostname = subprocess.check_output(["hostname"]).decode("utf-8")

        # use the activationID and activationCode to register the tenant by running sudo -E amazon-ssm-agent -register -code $code -id $id -region $region
        command = "sudo -E amazon-ssm-agent -register -code {} -id {} -region {}".format(
            activation_code, activation_id, region
        )
        os.system(command)
        instanceID = ""
        path = '/var/lib/amazon/ssm/registration'
        if os.path.exists(path):
            with open(path, 'r') as f:
                instance_data = json.load(f)
                instance_id = instance_data['ManagedInstanceID']
            instanceID = instance_id
            test = save_registration_details(
                instanceID, theater_id, theater_name, theater_email, hostname)
        else:
            prRed("Error: Registration file not found")
            sys.exit(1)

        prGreen("Successfully registered Theater")
        # clean_up()
    elif os.name == "nt":

        tempPath = os.getenv("TEMP")

        subprocess.call(
            [
                "powershell",
                "Invoke-WebRequest",
                "https://amazon-ssm-ap-south-1.s3.ap-south-1.amazonaws.com/latest/windows_amd64/AmazonSSMAgentSetup.exe",
                "-OutFile",
                ".\AmazonSSMAgentSetup.exe",
            ]
        )
        # Start-Process .\AmazonSSMAgentSetup.exe -ArgumentList @("/q", "/log", "install.log", "CODE=$code", "ID=$id", "REGION=$region") -Wait

        subprocess.call(
            [
                "powershell",
                "Start-Process",
                ".\AmazonSSMAgentSetup.exe",
                "-ArgumentList",
                '@("/q", "/log", "install.log", "CODE={}", "ID={}", "REGION={}")'.format(
                    activation_code, activation_id, region
                ),
                "-Wait",
            ]
        )
        hostname = subprocess.check_output(["hostname"]).decode("utf-8")
        with open(os.getenv("PROGRAMDATA") + "\\Amazon\\SSM\\InstanceData\\registration", "r") as f:
            data = f.read()
            data = json.loads(data)
            instance_id = data["ManagedInstanceID"]
            region = data["Region"]
            print(instance_id)
        test = save_registration_details(
            instance_id, theater_id, theater_name, theater_email, hostname)
        # Get-Content ($env:ProgramData + "\Amazon\SSM\InstanceData\registration")
        # subprocess.call(
        #     [
        #         "powershell",
        #         "Get-Content",
        #         os.getenv("ProgramData") +
        #         "\Amazon\SSM\InstanceData\registration",
        #     ]
        # )
        # # Get-Service -Name "AmazonSSMAgent"
        # subprocess.call(["powershell", "Get-Service",
        #                 "-Name", "AmazonSSMAgent"])
        # clean_up()
    else:
        prRed("Error: OS not supported")
        sys.exit(1)
    # download amazon-ssm-agent.deb from https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/debian_amd64/amazon-ssm-agent.deb
    # download from url
    # url = "https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/debian_amd64/amazon-ssm-agent.deb"
    # r = requests.get(url, allow_redirects=True)
    # open('amazon-ssm-agent.deb', 'wb').write(r.content)


# check up function to delete amazon-ssm-agent.deb , get-pip.py and storage.json. Uninstall the package requests and delete the file


def clean_up():
    prYellow("Cleaning up")
    if os.name == "posix":
        # remove amazon-ssm-agent.deb, get-pip.py and storage.json if present
        if os.path.isfile("amazon-ssm-agent.deb"):
            os.remove("amazon-ssm-agent.deb")
            prGreen("Successfully removed amazon-ssm-agent.deb")
        if os.path.isfile("get-pip.py"):
            os.remove("get-pip.py")
            prGreen("Successfully removed get-pip.py")
        if os.path.isfile("storage.json"):
            os.remove("storage.json")
            prGreen("Successfully removed storage.json")
        # uninstall requests
        subprocess.call(["sudo", "pip", "uninstall", "-y", "requests"])
        print(
            "\033[48;5;236m\033[38;5;231mThe script seems to have completed successfully, please check the status of SSM agent by running \033[38;5;208m'systemctl status amazon-ssm-agent'\033[0;0m"
        )
        dir = os.getcwd()
        os.remove(dir + "/%s" % sys.argv[0])
        sys.exit(1)
    elif os.name == "nt":
        # os.getenv("TEMP") + '\SSMAgent_latest.exe'

        # remove amazon-ssm-agent.deb, get-pip.py and storage.json if present
        if os.path.isfile(os.getenv("TEMP") + "\SSMAgent_latest.exe"):
            os.remove(os.getenv("TEMP") + "\SSMAgent_latest.exe")
            prGreen("Successfully removed amazon-ssm-agent.deb")
        if os.path.isfile(os.getenv("TEMP") + "\get-pip.py"):
            os.remove(os.getenv("TEMP") + "\get-pip.py")
            prGreen("Successfully removed get-pip.py")
        if os.path.isfile(os.getenv("TEMP") + "\storage.json"):

            os.remove(os.getenv("TEMP") + "\storage.json")
            prGreen("Successfully removed storage.json")
        # uninstall requests
        subprocess.call(["powershell", "pip", "uninstall", "-y", "requests"])
        print(
            "\033[48;5;236m\033[38;5;231mThe script seems to have completed successfully, please check the status of SSM agent by running \033[38;5;208m'systemctl status amazon-ssm-agent'\033[0;0m"
        )
        dir = os.getcwd()
        os.remove(dir + "/%s" % sys.argv[0])
        sys.exit(1)
    else:
        prRed("Error: OS not supported")
        sys.exit(1)


def stop_ssm_agent():
    prYellow("Stopping ssm agent")
    subprocess.call(["sudo", "amazon-ssm-agent", "stop"])


def start_ssm_agent():
    prYellow("Starting ssm agent")
    subprocess.call(["sudo", "amazon-ssm-agent", "start"])


def save_registration_details(machine_id, theater_id, theater_name, theater_email, hostname):
    prYellow("Saving activation details")
    import requests

    url = "{{ SAVE_ACTIVATION_URL }}"
    # url = "https://pq5ymlotdc.execute-api.ap-south-1.amazonaws.com/Prod/ssmactivation"
    payload = {"machine_id": machine_id,
               "theater_id": theater_id, "theater_name": theater_name, "theater_email": theater_email, "hostname": hostname}
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        prGreen("Successfully saved activation details")
        print(response.json())
        return response.json()
    else:
        prRed("Error: {}".format(response.json()))
        sys.exit(1)


def run():
    try:

        if os.name == "posix":
            os_name = "LINUX/OnPrem"
        elif os.name == "nt":
            os_name = "WINDOWS/OnPrem"

        # ask for theater id and tenant name from user
        # theater_id = input("Enter theater id: ")
        theater_id = str(input("Enter theater id: "))
        if theater_id.isdigit():
            raise ValueError("Theater id should not be a number")

        theater_name = str(input("Enter theater name: "))
        theater_email = str(input("Enter theater email: "))

        # theater_id = "theater-1"

        # tenant_name = "Services-Tenant"
        activation_details = get_activation_details(
            theater_id, os_name, theater_name)
        # check os path /lib/systemd/system/amazon-ssm-agent.service
        if os.name == "posix":
            if os.path.exists("/lib/systemd/system/amazon-ssm-agent.service"):
                prGreen("SSM agent is already installed")
                # create_cloudwatch_alarms("storage.json")
                reRegister(activation_details, theater_id, theater_name)
                # clean_up()
            else:
                prRed("SSM agent is not installed")
                install_ssm_agent(activation_details, theater_id,
                                  theater_name, theater_email)
                sys.exit(1)
        elif os.name == "nt":
            # check for path C:\ProgramData\Amazon\SSM\InstanceData
            hostanme = subprocess.check_output(
                ["powershell", "hostname"]).decode("utf-8").strip()

            if os.path.exists(os.getenv("PROGRAMDATA") + "\Amazon\SSM\InstanceData"):
                # read file registration and parse the json to get instanceID from {"ManagedInstanceID":"mi-065997545cc7a09b3","Region":"ap-south-1"}

                with open(os.getenv("PROGRAMDATA") + "\\Amazon\\SSM\\InstanceData\\registration", "r") as f:
                    data = f.read()
                    data = json.loads(data)
                    instance_id = data["ManagedInstanceID"]
                    region = data["Region"]
                    print(instance_id)
                test = save_registration_details(
                    instance_id, theater_id, theater_name, theater_email, hostanme)
                prGreen(
                    "SSM agent is already installed and the machine ID is {}".format(instance_id))
                # create_cloudwatch_alarms("storage.json")
                # reRegister(activation_details, theater_id, theater_name)
                # clean_up()
            else:
                prRed("SSM agent is not installed")
                install_ssm_agent(activation_details, theater_id,
                                  theater_name, theater_email)
                sys.exit(1)
        else:
            prRed("Error: OS not supported")
            sys.exit(1)

    except Exception as e:
        prRed("Error: {}".format(e))
        sys.exit(1)


def reRegister(activation, theater_id, theater_name):
    activation_id = activation["ActivationId"]
    activation_code = activation["ActivationCode"]
    region = "ap-south-1"

    service = "amazon-ssm-agent"
    if os.name == "posix":
        # use os.system to run the command
        command = "echo yes | sudo amazon-ssm-agent -register -code {} -id {} -region ap-south-1".format(
            activation_code, activation_id
        )
        os.system(command)
        # restart the service
        command = "sudo systemctl restart {}".format(service)
        os.system(command)

        # check if the service is active
        isActive = subprocess.check_output(
            ["systemctl", "is-active", "amazon-ssm-agent"]
        )
        isActive = isActive.decode("utf-8")
        isActive = isActive.strip()
        hostname = subprocess.check_output(
            ["hostname"]).decode("utf-8").strip()

        if isActive == "active":

            instanceID = ""
            path = '/var/lib/amazon/ssm/registration'
            if os.path.exists(path):
                with open(path, 'r') as f:
                    instance_data = json.load(f)
                    instance_id = instance_data['ManagedInstanceID']
                instanceID = instance_id
                test = save_registration_details(
                    instanceID, theater_id, theater_name, theater_email, hostname)
            prGreen("SSM agent is active")

        else:
            prRed("SSM agent is not installed")
            sys.exit(1)
    elif os.name == "nt":
        # use subprocess.call to run the command 'yes' | & 'C:\Program Files\Amazon\SSM\amazon-ssm-agent.exe' -register -code activation-code -id activation-id -region region; Restart-Service AmazonSSMAgent
        subprocess.call(
            [
                "yes",
                "|",
                "C:\\Program Files\\Amazon\\SSM\\amazon-ssm-agent.exe",
                "-register",
                "-code",
                activation_code,
                "-id",
                activation_id,
                "-region",
                region,
            ]
        )

        sys.exit(1)


def main():
    # check if package requests is installed if not install it and then call all the functions

    prYellow("Checking requirements")
    try:
        import requests

        prGreen("All required modules available")
        prYellowC(
            "Do you want to install ssm agent? \033[38;5;208m Type '1' for YES / '2' for NO :\033[0;0m"
        )
        choice = input()
        if choice == "1":
            run()
        elif choice == 2:
            prYellowC(
                "Do you want to create cloudwatch alarms? \033[38;5;208m Type '1' for YES / '2' for NO :\033[0;0m"
            )
            choice = input()
            if choice == "1":
                tenant_list = ["Services-Tenant", "Star-Tenant"]
                # create menu to select tenant
                print(
                    "\033[48;5;236m\033[38;5;231mSelect the tenant to register with SSM agent\033[0;0m"
                )
                for i, tenant in enumerate(tenant_list):
                    print(
                        "\033[48;5;236m\033[38;5;231m{}. {}\033[0;0m".format(
                            i + 1, tenant
                        )
                    )
                tenant_choice = int(
                    input(
                        "\033[48;5;236m\033[38;5;231mEnter your choice: \033[0;0m")
                )
                if tenant_choice > len(tenant_list):
                    prRed("Invalid choice")
                    sys.exit(1)
                tenant_name = tenant_list[tenant_choice - 1]
                # clean_up()

            elif choice == 2:
                sys.exit(1)
            else:
                prRed("Wrong input")
                sys.exit(1)
        else:
            prRed("Wrong input")
            sys.exit(1)
    except ImportError:
        prRed("Requests package is not installed. Installing it now")
        # install pip using curl https://bootstrap.pypa.io/pip/2.7/get-pip.py --output get-pip.py
        # run python get-pip.py
        url = "https://bootstrap.pypa.io/pip/2.7/get-pip.py"
        subprocess.call(["curl", url, "--output", "get-pip.py"])
        subprocess.call(["python", "get-pip.py"])

        subprocess.call(["pip", "install", "requests"])
        prGreen("Successfully installed requests")
        import requests

        # ask user input of 1 or 2 to install ssm agent or to run create_cloudwatch_alarms function
        prYellowC(
            "Do you want to install ssm agent? \033[38;5;208m Type '1' for YES / '2' for NO :\033[0;0m"
        )
        choice = input()
        if choice == "1":
            run()
        elif choice == 2:
            prYellowC(
                "Do you want to create cloudwatch alarms? \033[38;5;208m Type '1' for YES / '2' for NO :\033[0;0m"
            )
            choice = input()
            if choice == "1":
                tenant_list = ["Services-Tenant", "Star-Tenant", "New-Tenant"]
                # create menu to select tenant
                print(
                    "\033[48;5;236m\033[38;5;231mSelect the tenant to register with SSM agent\033[0;0m"
                )
                for i, tenant in enumerate(tenant_list):
                    print(
                        "\033[48;5;236m\033[38;5;231m{}. {}\033[0;0m".format(
                            i + 1, tenant
                        )
                    )
                tenant_choice = int(
                    input(
                        "\033[48;5;236m\033[38;5;231mEnter your choice: \033[0;0m")
                )
                if tenant_choice > len(tenant_list):
                    prRed("Invalid choice")
                    sys.exit(1)
                tenant_name = tenant_list[tenant_choice - 1]
                # clean_up()
            elif choice == 2:
                sys.exit(1)
            else:
                prRed("Wrong input")
                sys.exit(1)
        else:
            prRed("Wrong input")
            sys.exit(1)


if __name__ == "__main__":
    main()
    sys.exit(1)


# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
# vi: set ft=python:
# EOF
