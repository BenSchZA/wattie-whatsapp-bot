import subprocess


def send_whatsapp(number, message=None, url=None, media=None):
    process = "./venv/bin/python whatsapp_cli.py --number %s" % number

    if message:
        process += " --message %s" % message
    if url:
        process += " --url %s" % url
    if media:
        process += " --media %s" % media

    try:
        subprocess.check_output([process], shell=True)
        return True
    except subprocess.CalledProcessError as e:
        print(e)
        return False
