sudo apt install -y default-mysql-client
sudo apt install -y default-mysql-server
read -sp 'Create password for user: ' p
echo
sudo mysql -u root -e "CREATE USER user@localhost IDENTIFIED BY '$p';"
sudo mysql -u root -e "GRANT ALL PRIVILEGES ON *.* TO 'user'@'localhost';"
mysql -u user -p$p -e "CREATE DATABASE IF NOT EXISTS library;"