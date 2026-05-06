read -p 'ENTER BASE URL: ' base
primary=("libavtor" "libtranslator" "libavtorname" "libbook" "libfilename" "libgenre" "libgenrelist" "libjoinedbooks" "libseqname" "libseq")
annotations=("b.annotations" "a.annotations")
user=("librate" "librecs" "reviews")
annotations_ok=true
user_ok=true

FAILED=()


confirm() {
	local prompt="${1}"
	local yn
	while true; do
		read -p "$prompt [y/n]: " yn
		case "$yn" in
			[Yy]* ) return 0 ;;
			[Nn]* ) return 1 ;;
			* ) echo "PLEASE ANSWER YES OR NO." >&2 ;;
		esac
	done
}

check_sql_archives() {
	local arr=("$@")
	local changed_files=()
	for table in "${arr[@]}"; do
		echo $table >&2
		local remote_url="$base/sql/lib.$table.sql.gz"
		local local_file="./sql/lib.$table.sql.gz"
		response=$(curl -sI --retry 3 "$remote_url")
		http_code=$(echo "$response" | awk 'NR==1 {print $2}' | tr -d '\r')
		if [ "$http_code" -eq 200 ]; then
			remote_size=$(echo "$response" | awk '/[Cc]ontent-[Ll]ength/ { print $2 }' | tr -d '\r')
			if ((remote_size > 5000)); then
				if [ -f "$local_file" ]; then
					local_size=$(stat -c%s "$local_file")
				else
					local_size=0
				fi
				if [ "$remote_size" != "$local_size" ]; then
					echo "  UPDATE(${local_size}->${remote_size})" >&2
					changed_files+=("$table")
				else
					echo "  ALREADY(${remote_size})" >&2
				fi
			else
				echo "  FAIL($remote_size)" >&2
				FAILED+=("$table")
				return 1
			fi
		else
			echo "  FAIL($http_code)" >&2
			FAILED+=("$table")
			return 1
		fi
	done
	echo "${changed_files[@]}"
	return 0
}

download_sql_archives() {
	local arr=("$@")
	for table in "${arr[@]}"; do
		echo "DOWNLOADING $table" >&2
		file=lib."$table".sql.gz
		if wget --tries=3 -P sqltmp "$base/sql/$file" && gzip -t "sqltmp/$file"; then
			mv -f "sqltmp/$file" "sql/$file"
			echo "  SUCCESS" >&2
		else
			echo "  FAIL" >&2
			rm -f "sqltmp/$file"
			FAILED+=("$table")
		fi
	done
}

check_single_file() {
	local remote_url=$1
	local local_file=$2
	response=$(curl -sI --retry 3 "$remote_url")
	http_code=$(echo "$response" | awk 'NR==1 {print $2}' | tr -d '\r')
	if [ "$http_code" -eq 200 ]; then
		remote_size=$(echo "$response" | awk '/[Cc]ontent-[Ll]ength/ { print $2 }' | tr -d '\r')
		if ((remote_size > 5000)); then
			if [ -f "$local_file" ]; then
				local_size=$(stat -c%s "$local_file")
			else
				local_size=0
			fi
			if [ "$remote_size" != "$local_size" ]; then
				echo "  UPDATE(${local_size}->${remote_size})" >&2
				return 0
			else
				echo "  ALREADY(${remote_size})" >&2
				return 1
			fi
		else
			echo "  FAIL(size=$remote_size)" >&2
			FAILED+=("$local_file")
			return 1
		fi
	else
		echo "  FAIL(code=$http_code)" >&2
		FAILED+=("$local_file")
		return 1
	fi
}

download_single_file() {
	local remote_url=$1
	local local_file=$2
	echo "DOWNLOADING $local_file" >&2
	if wget --tries=3 -P sqltmp "$remote_url" && { [[ "$local_file" == *.zip ]] && unzip -tq "sqltmp/$local_file" || gzip -t "sqltmp/$local_file"; }; then
		mv -f "sqltmp/$local_file" "sql/$local_file"
		echo "  SUCCESS" >&2
	else
		echo "  FAIL" >&2
		rm -f "sqltmp/$local_file"
		FAILED+=("$local_file")
	fi
}

mkdir -p sql
mkdir -p sqltmp

#primary
echo "TESTING PRIMARY TABLES..."
changed_tables=( $(check_sql_archives "${primary[@]}") )
exit_status=$?
if [ $exit_status -eq 0 ]; then
	if [ -z "$changed_tables" ]; then
		echo "PRIMARY TABLES OK; EVERYTHING UP TO DATE."
	else
		echo "PRIMARY TABLES OK; DOWNLOADING: ${changed_tables[*]}"
		download_sql_archives "${changed_tables[@]}"
		echo "PRIMARY TABLES DOWNLOADED"
	fi
else
	echo "PRIMARY TABLES INCOMPLETE; QUITTING!"
	exit
fi

#catalog
echo "TESTING CATALOG..."
check_single_file "$base"/catalog/catalog.zip ./sql/catalog.zip
exit_status=$?
if [ $exit_status -eq 0 ]; then
	echo "DOWNLOADING CATALOG..."
	download_single_file "$base"/catalog/catalog.zip catalog.zip
else
	echo "SKIPPING!"
fi

#annotations
if confirm "DOWNLOAD ANNOTATION TABLES?"; then
	echo "TESTING ANNOTATION TABLES..."
	changed_tables=( $(check_sql_archives "${annotations[@]}") )
	exit_status=$?
	if [ $exit_status -eq 0 ]; then
		if [ -z "$changed_tables" ]; then
			echo "ANNOTATION TABLES OK; EVERYTHING UP TO DATE."
		else
			echo "ANNOTATION TABLES OK; DOWNLOADING: ${changed_tables[*]}"
			download_sql_archives "${changed_tables[@]}"
			echo "ANNOTATION TABLES DOWNLOADED"
		fi
	else
		echo "ANNOTATION TABLES INCOMPLETE; SKIPPING!"
	fi
else
	echo "ABORTED BY USER!"
fi

#user
if confirm "DOWNLOAD USER TABLES?"; then
	echo "TESTING USER TABLES..."
	changed_tables=( $(check_sql_archives "${user[@]}") )
	exit_status=$?
	if [ $exit_status -eq 0 ]; then
		if [ -z "$changed_tables" ]; then
			echo "USER TABLES OK; EVERYTHING UP TO DATE."
		else
			echo "USER TABLES OK; DOWNLOADING: ${changed_tables[*]}"
			download_sql_archives "${changed_tables[@]}"
			echo "USER TABLES DOWNLOADED"
		fi
	else
		echo "USER TABLES INCOMPLETE; SKIPPING!"
	fi
else
	echo "ABORTED BY USER!"
fi

#md5
if confirm "DOWNLOAD MD5 LIST?"; then
	echo "TESTING MD5 LIST..."
	check_single_file "$base"/sql/lib.md5.txt.gz ./sql/lib.md5.txt.gz
	exit_status=$?
	if [ $exit_status -eq 0 ]; then
		download_single_file "$base"/sql/lib.md5.txt.gz lib.md5.txt.gz
		echo "MD5 LIST DOWNLOADED"
	else
		echo "SKIPPING!"
	fi
else
	echo "ABORTED BY USER!"
fi

rm -rf sqltmp

if [ ${#FAILED[@]} -ne 0 ]; then
	echo "SOME FAILED: ${FAILED[*]}"
else
	echo "EVERYTHING OK"
fi










