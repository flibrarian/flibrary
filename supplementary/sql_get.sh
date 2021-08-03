rm -r sql
mkdir sql
read -p 'Enter base url: ' b
for table in libavtor libtranslator libavtorname libbook libgenre libgenrelist libjoinedbooks libseqname libseq
do
	wget -P sql "$b"/sql/lib."$table".sql.gz
done
