# -*- coding: utf-8 -*-
# Copyright (C) 2009-2012 LibreSoft
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors :
#       Carlos Garcia Campos  <carlosgc@libresoft.es>
#       Santiago Dueñas <sduenas@libresoft.es>

from pycvsanaly2.Database import statement, ICursor

if __name__ == '__main__':
    import sys
    sys.path.insert (0, "../../")

class FileRevs:

    INTERVAL_SIZE = 1000
    __query__ = '''select s.rev rev, s.id commit_id, af.file_id, af.action_type, s.composed_rev 
from scmlog s, action_files af where s.id = af.commit_id and s.repository_id = ? order by s.id'''
    # This query selects the newest entry for those cases with two filepaths
    # for the same file. See https://github.com/MetricsGrimoire/CVSAnalY/issues/3 for more info.
    __path_query__ = '''SELECT file_path FROM file_links,
(SELECT MAX(id) id FROM file_links WHERE file_id = ? AND commit_id <= ? ORDER BY commit_id DESC) fp
WHERE file_links.id = fp.id'''

    def __init__ (self, db, cnn, cursor, repoid):
        self.db = db
        self.cnn = cnn
        self.repoid = repoid

        self.icursor = ICursor (cursor, self.INTERVAL_SIZE)
        self.icursor.execute (statement (self.__query__, db.place_holder), (repoid,))
        self.rs = iter (self.icursor.fetchmany ())
        self.prev_commit = -1
        self.current = None

    def __iter__ (self):
        return self

    def __get_next (self):
        try:
            t = self.rs.next ()
        except StopIteration:
            self.rs = iter (self.icursor.fetchmany ())
            if not self.rs:
                raise StopIteration
            t = self.rs.next ()

        return t

    def next (self):
        if not self.rs:
            raise StopIteration

        self.current = self.__get_next ()
        return self.current

    def get_path(self):
        if not self.current:
            return None

        revision, commit_id, file_id, action_type, composed = self.current
        if composed:
            rev = revision.split("|")[0]
        else:
            rev = revision

        relative_path = self.__get_path_from_db(file_id, commit_id).strip("/")

        return relative_path
    
    def __get_path_from_db(self, file_id, commit_id):
        cursor = self.cnn.cursor()

        cursor.execute(statement(self.__path_query__, self.db.place_holder),
                       (file_id, commit_id))
        path = cursor.fetchone()[0]

        cursor.close ()

        return "/" + path

if __name__ == '__main__':
    import sys
    from pycvsanaly2.Database import create_database
    from pycvsanaly2.Config import Config

    config = Config ()
    config.load ()
    db = create_database (config.db_driver, sys.argv[1], config.db_user, config.db_password, config.db_hostname)
    cnn = db.connect ()
    cursor = cnn.cursor ()

    fr = FileRevs (db, cnn, cursor, 1)
    for revision, commit_id, file_id, action_type, composed in fr:
        print revision, commit_id, action_type, fr.get_path ()

    cursor.close ()
    cnn.close ()
