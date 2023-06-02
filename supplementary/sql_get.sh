read -p 'ENTER BASE URL: ' b
primary=("libavtor" "libtranslator" "libavtorname" "libbook" "libfilename" "libgenre" "libgenrelist" "libjoinedbooks" "libseqname" "libseq")
annotations=("b.annotations" "a.annotations")
user=("librate" "librecs" "reviews")
primary_ok=true
annotations_ok=true
user_ok=true

#primary

echo "TESTING PRIMARY TABLES..."
for table in ${primary[@]}; do
	echo $table
	table_size=`curl -sI "$b"/sql/lib."$table".sql.gz | awk '/[Cc]ontent-[Ll]ength/ { print $2 }'`
	table_size=${table_size::-1}
	if ((table_size > 5000)); then
		echo "  OK(${table_size})"
	else
		primary_ok=false
		echo "  FAIL($table_size)"
	fi
done
if ! $primary_ok; then
	echo "PRIMARY TABLES INCOMPLETE; QUITTING!"
	exit
fi
echo "PRIMARY TABLES OK; DOWNLOADING..."
rm -r sql
mkdir sql
for table in ${primary[@]}; do
	echo $table
	wget -NcP sql "$b"/sql/lib."$table".sql.gz
done
echo "PRIMARY TABLES DOWNLOADED"

#annotations

echo "TESTING ANNOTATION TABLES..."
for table in ${annotations[@]}; do
	echo $table
	table_size=`curl -sI "$b"/sql/lib."$table".sql.gz | awk '/[Cc]ontent-[Ll]ength/ { print $2 }'`
	table_size=${table_size::-1}
	if ((table_size > 5000)); then
		echo "  OK(${table_size})"
	else
		annotations_ok=false
		echo "  FAIL($table_size)"
	fi
done
if $annotations_ok; then
while true; do
	read -p "DOWNLOAD ANNOTATION TABLES? " yn
	case $yn in
		[Yy]* )
			echo "DOWNLOADING ANNOTATION TABLES..."
			for table in ${annotations[@]}; do
				echo $table
				wget -P sql "$b"/sql/lib."$table".sql.gz
			done
			break;;
		[Nn]* )
			break;;
		* ) echo "PLEASE ANSWER YES OR NO.";;
	esac
done
else
	echo "ANNOTATION TABLES INCOMPLETE; SKIPPING"
fi

#user

echo "TESTING USER TABLES..."
for table in ${user[@]}; do
	echo $table
	table_size=`curl -sI "$b"/sql/lib."$table".sql.gz | awk '/[Cc]ontent-[Ll]ength/ { print $2 }'`
	table_size=${table_size::-1}
	if ((table_size > 5000)); then
		echo "  OK(${table_size})"
	else
		user_ok=false
		echo "  FAIL($table_size)"
	fi
done
if $user_ok; then
while true; do
	read -p "DOWNLOAD USER TABLES? " yn
	case $yn in
		[Yy]* )
			echo "DOWNLOADING USER TABLES..."
			for table in ${user[@]}; do
				echo $table
				wget -P sql "$b"/sql/lib."$table".sql.gz
			done
			break;;
		[Nn]* )
			break;;
		* ) echo "PLEASE ANSWER YES OR NO.";;
	esac
done
else
	echo "USER TABLES INCOMPLETE; SKIPPING"
fi
echo "TESTING MD5 LIST..."
	echo "md5.txt"
	list_size=`curl -sI "$b"/sql/lib.md5.txt.gz | awk '/[Cc]ontent-[Ll]ength/ { print $2 }'`
	list_size=${list_size::-1}
	if ((list_size > 5000)); then
		echo "  OK(${list_size})"
		while true; do
			read -p "DOWNLOAD MD5 LIST? " yn
			case $yn in
				[Yy]* )
					echo "DOWNLOADING MD5 LIST..."
					wget -P sql "$b"/sql/lib.md5.txt.gz
					break;;
				[Nn]* )
					break;;
				* ) echo "PLEASE ANSWER YES OR NO.";;
			esac
		done
	else
		user_ok=false
		echo "  FAIL($list_size)"
	fi
echo "TESTING CATALOG..."
	echo "catalog.zip"
	list_size=`curl -sI "$b"/catalog/catalog.zip | awk '/[Cc]ontent-[Ll]ength/ { print $2 }'`
	list_size=${list_size::-1}
	if ((list_size > 5000)); then
		echo "  OK(${list_size})"
		while true; do
			read -p "DOWNLOAD CATALOG? " yn
			case $yn in
				[Yy]* )
					echo "DOWNLOADING CATALOG..."
					wget -P sql "$b"/catalog/catalog.zip
					break;;
				[Nn]* )
					break;;
				* ) echo "PLEASE ANSWER YES OR NO.";;
			esac
		done
	else
		user_ok=false
		echo "  FAIL($list_size)"
	fi

















