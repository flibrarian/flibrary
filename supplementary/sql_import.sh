read -sp 'Enter password for user: ' p
echo 
for table in libavtor libtranslator libavtorname libbook libgenre libgenrelist libjoinedbooks libseqname libseq
do
	echo "$table"
	zcat sql/lib."$table".sql.gz | mysql -u 'user' -p$p  library
done
while true; do
	read -p "Import annotations?" yn
	case $yn in
		[Yy]* ) break;;
		[Nn]* ) exit;;
		* ) echo "Please answer yes or no.";;
	esac
done
for table in b.annotations
do
	echo "$table"
	zcat sql/lib."$table".sql.gz | mysql -u 'user' -p$p  library
done
