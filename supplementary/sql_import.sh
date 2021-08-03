read -sp 'Enter password for user: ' p
echo 
for table in libavtor libtranslator libavtorname libbook libgenre libgenrelist libjoinedbooks libseqname libseq
do
	echo "$table"
	zcat sql/lib."$table".sql.gz | mysql -u 'user' -p$p  library
done
