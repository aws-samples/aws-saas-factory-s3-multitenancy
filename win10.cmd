## Commands post installation of aws cli tool
cmd
Set-ExecutionPolicy -Scope CurrentUser
RemoteSigned
Import-Module AWSPowerShell
Set-AWSCredential `
    -AccessKey <AccessKey> `
    -SecretKey <SecretKey> `
    -StoreAs <ProfileName>

aws configure
[Enter Access Key]
[Enter Secret Key]
[Enter Default Reqion]
[Hit Enter]


