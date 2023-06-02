read -sp 'ENTER PASSWORD FOR USER: ' p
echo 
primary=("libavtor" "libtranslator" "libavtorname" "libbook" "libfilename" "libgenre" "libgenrelist" "libjoinedbooks" "libseqname" "libseq")
annotations=("b.annotations" "a.annotations")
user=("librate" "librecs" "reviews")
for table in ${primary[@]}; do
	echo "$table"
	zcat sql/lib."$table".sql.gz | mysql -u 'user' -p$p  library
done
while true; do
	read -p "IMPORT ANNOTATION TABLES? " yn
	case $yn in
		[Yy]* )
			for table in ${annotations[@]}; do
				echo "$table"
				zcat sql/lib."$table".sql.gz | mysql -u 'user' -p$p  library
			done
			break;;
		[Nn]* ) break;;
		* ) echo "Please answer yes or no.";;
	esac
done
while true; do
	read -p "IMPORT USER TABLES? " yn
	case $yn in
		[Yy]* )
			for table in ${user[@]}; do
				echo "$table"
				zcat sql/lib."$table".sql.gz | mysql -u 'user' -p$p  library
			done
			break;;
		[Nn]* ) break;;
		* ) echo "Please answer yes or no.";;
	esac
done

