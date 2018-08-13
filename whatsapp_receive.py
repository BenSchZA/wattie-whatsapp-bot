#!/usr/bin/env python3

import time
import datetime
import dateutil.parser
from difflib import SequenceMatcher

from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as exp_c
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.keys import Keys

import pymongo
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import WriteError

# from session_manager import SessionManager
from whatsapp_message import WhatsAppMessage
import re
import requests
import os
import whatsapp_cli_interface

TIMEOUT = 60
MESSAGE_LIMIT = 5

binary = FirefoxBinary('/usr/bin/firefox-developer-edition')
webdriver.DesiredCapabilities.FIREFOX["unexpectedAlertBehaviour"] = "accept"


class WhatsAppReceive:

    def __init__(self) -> None:
        super().__init__()

        self._initialize_database()

        # self.session = SessionManager
        # self.driver = self.session.get_existing_driver_session()

        self.driver = webdriver.Firefox(firefox_binary=binary)
        self.driver.get('https://web.whatsapp.com/')

        self.wait = WebDriverWait(self.driver, TIMEOUT)

        self.processed_conversation_ids = []
        self.previous_conversation_content = None

        self.processed_contacts = []

    def _initialize_database(self):
        self.client = MongoClient('localhost', 27017)
        self.db = self.client.whatsapp_cli

        # MongoDB scales horizontally, so: single messages collection containing all messages from all conversations
        self.messages_collection: Collection = self.db.messages
        self.messages_collection.create_index([("uid", pymongo.DESCENDING), ("timestamp", pymongo.DESCENDING),
                                               ("content", pymongo.DESCENDING)], unique=True)

    def process_contacts(self):
        # self._for_each_conversation(self._process_contact)
        # print(self.processed_contacts)
        self.processed_contacts = ['+27 82 401 5858', 'Feedback ***REMOVED***', '+27 76 073 7507', '+27 83 440 4460', '+27 72 809 0803', '+27 72 125 8529', '+27 72 707 7226', '+27 82 738 9254', '+27 71 860 2199', '+27 72 064 1175', '+27 74 131 9836', '+27 74 806 2109', '+27 73 156 8484', '+27 78 127 3813', '+27 76 601 5529', '+27 82 817 8775', '+27 71 431 0522', '+27 72 808 5882', '+27 71 362 0481', '+27 61 050 7225', '+27 71 401 2356', '+27 81 010 7588', '+27 79 697 3950', '+27 82 312 6171', '+27 83 598 6501', '+27 71 334 7773', '+27 83 507 4327', '+27 83 630 5926', '+27 83 407 6568', '+27 76 933 7785', '+27 76 390 1788', '+27 79 239 5788', '+27 72 285 1202', '+27 79 774 0555', '+44 7557 633878', '+27 84 492 0537', '+27 82 495 5921', '+27 82 461 2155', '+27 72 358 5256', '+27 82 567 8401', '+27 73 573 6299', '+27 83 441 2032', '+44 7795 092589', '+27 71 543 9403', '+27 83 783 2169', '+27 81 504 7505', '+27 72 502 1279', '+44 7480 181670', '+27 72 590 9692', '+27 79 889 5093', '+27 71 440 4344', '+27 71 858 6870', '+27 79 963 9677', '+27 76 814 2312', '+27 83 785 7464', '+27 73 968 7599', '+238 912 24 10', '+27 76 446 1028', '+27 82 805 5822', '+27 79 362 7175', '+27 83 325 1577', '+27 72 513 2766', '+27 79 298 0120', '+27 78 166 3432', '+27 82 551 3815', '+27 79 695 3713', '+27 74 198 1881', '+27 72 724 5179', '+27 79 214 2003', '+27 83 410 6171', '+27 84 654 6274', '+27 72 146 5519', '+27 60 673 2792', '+27 71 869 9797', '+27 71 252 2441', '+27 83 612 2182', '+27 72 361 6336', '+27 73 349 5496', '+27 72 521 6953', '+27 82 333 8290', '+27 83 267 6954', '+27 72 943 2373', '+27 79 194 8785', '+27 83 382 8444', '+27 83 620 7388', '+27 72 268 0211', '+27 82 552 9190', '+27 61 266 2006', '+27 82 975 7761', '+27 76 792 6435', '+27 84 205 6541', '+27 78 458 0157', '+27 82 528 3606', '+27 72 685 0447', '+27 76 338 1243', '+27 83 260 8668', '+27 82 303 1591', '+27 76 252 7652', '+27 73 873 6241', '+27 76 991 5473', '+27 76 782 7750', '+27 81 022 0868', '+27 83 294 8011', '+27 82 070 3601', '+27 82 744 6107', '+27 82 559 8478', '+27 83 643 1591', '+27 73 335 5592', '+27 72 049 5291', '+27 78 283 2172', '+27 71 641 1764', '+27 63 912 1610', '+27 84 841 0296', '+27 76 312 3940', '+27 82 557 1630', '+27 83 616 6004', '+27 74 775 3256', '+27 84 621 7292', '+44 7880 138544', '+27 76 399 7611', '+27 73 847 0730', '+27 76 250 0887', '+27 72 441 1772', '+27 83 778 7509', '+27 83 601 6862', '+27 81 267 3222', '+27 76 829 4877', '+27 83 792 5465', '+27 79 501 4683', '+27 73 404 1104', '+27 72 100 9474', '+27 82 975 4217', '+27 83 981 3296', '+27 82 702 2246', '+27 79 519 7100', '+27 84 400 1210', '+27 83 658 4957', '+27 71 572 5988', '+353 83 885 6327', '+27 74 588 7141', '+27 83 679 4651', '+27 72 257 7040', '+27 71 609 4635', '+27 76 461 4128', '+27 72 315 1270', '+27 79 881 2355', '+27 83 269 2367', '+27 71 609 6440', '+27 76 340 2538', '+27 82 866 8972', '+27 73 136 6159', '+27 71 038 7866', '+27 84 522 4906', '+27 71 364 6976', '+27 73 632 9759', '+27 71 351 1620', '+27 76 472 7479', '+27 76 974 2456', '+27 82 443 4370', '+27 81 431 0160', '+27 74 134 5952', '+27 82 964 6242', '+27 82 319 0359', '+44 7482 940672', '+44 7378 779994', '+27 83 465 9449', '+27 79 667 7145', '+27 78 035 8472', '+27 76 807 9417', '+27 84 568 9193', '+27 76 082 5122', '+27 83 278 5992', '+27 83 575 1500', '+27 79 766 2479', '+27 71 147 2303', '+27 79 790 7373', '+27 82 296 6008', '+27 72 731 8694', '+27 76 212 2765', '+27 66 223 1882', '+27 73 315 4037', '+27 65 169 6168', '+27 74 187 1076', '+27 82 432 9879', '+27 73 318 4090', '+27 83 661 4949', '+27 83 443 0729', '+27 82 491 6895', '+27 78 059 2626', '+27 79 553 8995', '+27 72 592 5655', '+27 73 231 3174', '+27 60 997 3295', '+27 83 288 2330', '+27 83 408 3989', '+27 60 658 2920', '+27 84 016 9284', '+27 81 270 9491', '+27 82 462 0311', '+27 61 453 2156', '+27 79 933 6834', '+27 84 550 3846', '+27 76 106 1323', '+27 74 942 1267', '+27 83 238 5352', '+27 83 391 8186', '+44 7876 582807', '+27 82 424 5403', '+27 62 252 0829', '+27 76 903 4886', '+27 76 132 7953', '+27 83 436 0737', '+27 83 661 2183', '+27 82 559 8767', '+27 82 490 4987', '+27 62 468 7274', '+27 71 562 4454', '+27 84 583 3091', '+27 78 469 0640', '+27 74 299 4820', '+27 83 669 4011', '+27 71 112 5019', '+27 83 704 4167', '+27 82 920 9149', '+27 83 704 0607', '+44 7464 729094', '+27 79 394 8233', '+27 83 268 0989', '+27 73 264 8508', '+27 72 390 0355', '+27 76 829 2726', '+27 73 271 9904', '+27 79 093 0800', '+27 82 429 6648', '+1 (970) 379-3528', '+27 72 974 4829', '+27 83 976 3483', '+27 72 161 2246', '+27 71 242 3001', '+27 72 483 3380', '+27 82 323 6933', '+27 72 432 1693', '+27 76 210 7597', '+27 83 616 4079', '+27 76 979 9039', '+27 72 206 6950', '+27 71 523 6373', '+27 84 088 6666', '+27 82 574 5896', '+27 83 640 8579', '+27 71 317 7068', '+44 7400 440812', '+27 72 106 4174', '+27 83 656 8733', '+27 83 453 1655', '+27 82 788 2727', '+27 73 312 3180', '+27 72 377 0795', '+27 79 772 2103', '+27 84 539 9954', '+44 7957 419576', '+27 72 962 8246', '+27 83 327 5415', '+27 83 775 1251', '+27 82 451 6848', '+27 71 686 3942', '+27 76 908 9433', '+27 83 290 4731', '+27 72 686 3630', '+27 76 215 8482', '+27 78 193 2253', '+27 76 981 8868', '+267 71 875 500', '+27 73 884 7345', '+44 7851 856209', '+27 79 873 8069', '+27 73 988 6129', '+27 76 194 2579', '+27 82 524 8007', '+27 78 457 3287', '+27 82 445 0971', '+27 72 143 0675', '+27 84 257 2950', '+27 73 934 9659', '+27 72 610 1726', '+27 83 708 1723', '+1 (856) 701-0127', '+27 83 320 8073', '+27 83 662 6669', '+27 82 532 8465', '+27 83 679 3778', '+27 72 587 9780', '+27 74 140 3954', '+27 82 086 3837', '+27 82 730 3253', '+27 71 293 6757', '+27 60 524 5312', '+27 82 551 8551', '+27 83 288 9413', '+27 76 526 2701', '+27 82 373 3877', '+27 81 021 2674', '+27 71 134 5959', '+27 72 593 6289', '+27 76 339 0188', '+27 82 886 6547', '+27 76 953 0439', '+27 73 317 8687', '+27 82 926 4785', '+27 76 814 5942', '+27 71 689 1123', '+27 76 393 2587', '+27 78 218 8486', '+27 71 680 5981', '+27 71 166 7285', '+27 72 515 9543', '+27 79 802 8575', '+27 82 803 7676', '+27 72 267 0470', '+27 79 469 0607', '+27 82 049 5058', '+27 74 444 1588', '+27 83 254 9821', '+27 79 990 6644', '+1 (847) 804-2182', '+27 76 276 8066', '+27 73 050 4615', '+27 82 070 7061', '+27 82 484 4194', '+27 72 703 5447', '+27 62 331 9096', '+27 82 451 8041', '+27 84 653 0621', '+27 78 119 9259', '+27 60 942 1590', '+27 71 414 8477', '+27 83 641 9768', '+1 (612) 598-5133', '+27 84 083 0245', '+27 83 400 0214', '+27 82 778 0648', '+27 82 517 2909', '+27 83 778 1928', '+27 73 097 5938', '+27 83 723 4760', '+27 76 786 8246', '+27 76 428 0891', '+27 83 503 3556', '+27 82 072 9359', '+86 186 8931 3044', '+27 72 218 8240', '+27 82 444 9310', '+27 83 377 1625', '+27 84 562 1289', '+27 82 921 0904', '+27 83 470 0033', '+27 83 646 8924', '+27 73 958 3665', '+27 83 629 3806', '+27 76 680 8943', '+27 72 623 5374', '+27 71 152 1233', '+27 76 033 8962', '+27 83 208 8177', '+27 82 997 0202', '+27 72 552 9500', '+27 83 227 8808', '+27 82 315 3825', '+27 83 890 9997', '+27 84 513 2585', '+27 76 054 6606', '+44 7490 599562', '+27 83 655 5885', '+27 64 982 3334', '+27 82 424 2641', '+27 82 447 8625', '+27 83 649 8122', '+27 76 339 2072', '+27 82 681 0831', '+27 72 802 3733', '+27 72 690 6945', '+27 72 171 7502', '+27 82 810 4282', '+27 72 309 6454', '+27 82 654 5090', '+27 82 444 3668', '+27 76 765 3373', '+27 76 546 6362', '+44 7802 591562', '+27 83 302 6562', '+27 83 799 8133', '+44 7717 069698', '+27 74 589 5751', '+31 6 25542303', '+27 76 841 2166', '+27 61 529 5517', '+27 82 372 9509', '+254 729 406636', '+27 72 603 6565', '+27 76 903 8900', '+27 72 594 3791', '+264 81 129 4198', '+27 71 261 2777', '+27 74 291 5624', '+27 76 457 1433', '+27 84 907 0206', '+27 79 060 7985', '+27 82 866 4383', '+27 83 695 0440', '+27 72 271 5617', '+27 76 264 1503', '+27 61 798 5203', '+27 72 879 6256', '+27 71 252 2440', '+27 82 465 9237', '+27 71 351 4642', '+27 72 100 7365', '+27 83 285 4525', '+27 71 259 4505', '+27 76 898 8126', '+27 84 011 2999', '+27 72 706 7285', '+27 72 606 0849', '+27 72 317 5604', '+27 62 051 8052', '+27 72 235 8234', '+27 63 076 6989', '+27 83 529 3383', '+27 73 993 2253', '+27 78 431 6035', '+27 72 255 2972', '+27 79 037 4818', '+27 66 268 4344', '+27 83 772 3555', '+44 7557 564426', '+27 74 943 0809', '+27 84 903 4239', '+27 76 299 7577', '+27 76 473 8036', '+27 82 557 1745', '+27 83 255 0703', '+27 78 458 0456', '+27 74 113 4079', '+27 72 566 5265', '+27 83 642 9919', '+27 72 196 3324', '+27 72 252 9709', '+27 72 193 5008', '+27 79 524 9020', '+27 74 724 2213', '+27 82 092 6188', '+27 79 515 6344', '+27 71 687 5262', '+27 82 784 7595', '+27 78 456 1502', '+44 7961 298559', '+27 82 422 5011', '+27 82 857 6127', '+27 82 446 0564', '+27 83 604 2882', '+27 84 251 2548', '+27 73 148 3015', '+27 72 041 2224', '+27 82 573 4346', '+44 7733 764044', '+27 79 468 5667', '+27 82 908 7087', '+27 84 548 4828', '+27 63 245 9335', '+27 84 207 0633', '+27 82 616 1888', '+27 84 509 3478', '+27 72 452 6334', '+27 76 352 7676', '+27 83 229 4250', '+27 71 627 4233', '+27 72 614 4349', '+27 76 453 0288', '+27 81 491 9950', '+27 74 101 2090', '+27 72 427 9757', '+27 76 958 2839', '+27 71 203 1966', '+27 83 586 3979', '+27 72 342 7111', '+27 76 790 3335', '+27 83 605 9898', '+27 82 307 7715', '+27 61 636 8556', '+27 84 883 9243', '+27 79 525 5730', '+27 79 344 3953', '+31 6 21252107', '+27 73 598 7254', '+27 72 117 4999', '+27 72 117 4645', '+27 82 962 5919', '+27 72 060 2662', '+27 83 686 9515', '+27 63 887 7920', '+27 82 455 5505', '+44 7428 160051', '+27 79 962 1040', '+27 76 155 8606', '+27 71 851 6687', '+263 77 609 6189', '+27 73 281 4936', '+27 82 789 5023', '+27 72 658 9311', '+27 72 474 5096', '+27 82 554 3719', '+230 5939 9446', '+27 83 782 1847', '+27 71 415 9432', '+27 83 565 3669', '+27 76 927 5539', '+27 64 956 6119', '+44 7747 455486', '+27 84 847 7666', '+27 83 395 5207', '+27 79 772 5078', '+27 79 497 7634', '+27 83 796 7018', '+27 76 551 1667', '+27 76 908 7688', '+27 78 950 7901', '+27 83 474 5988', '+27 82 943 1891', '+27 82 083 1791', '+234 809 944 0777', '+27 79 773 1066', '+27 82 922 9046', '+44 7341 939936', '+27 82 574 7645', '+27 82 417 6708', '+44 7785 984265', '+27 82 457 1522', '+27 76 282 1662', '+27 74 475 9415', '+27 78 265 8128', '+27 82 781 7731', '+27 82 505 0944', '+27 72 471 0676', '+27 83 778 0294', '+27 71 174 4510', '+27 83 298 9554', '+27 76 221 5822', '+44 7490 911175', '+27 79 455 0434', '+27 60 504 4582', '+27 71 679 4457', '+27 71 403 9117', '+27 84 696 9161', '+27 82 442 6133', '+27 82 882 7897', '+27 83 231 8646', '+27 83 448 4883', '+27 71 347 4089', '+27 76 555 9180', '+27 72 037 6032', '+27 83 225 5305', '+27 79 690 0576', '+27 71 205 3988', '+27 79 344 0064', '+27 78 893 0000', '+27 78 185 4892', '+27 82 302 8167', '+44 7584 557571', '+27 76 379 1376', '+27 83 275 8628', '+44 7917 481242', '+27 74 619 9334', '+27 61 423 9803', '+27 72 774 6577', '+27 71 877 3262', '+27 72 086 3377', '+27 63 688 9878', '+27 82 726 5477', '+264 81 347 7018', '+27 63 687 5083', '+27 79 672 0317', '+27 83 222 7351', '+27 82 399 7763', '+27 71 383 0539', '+27 72 197 2014', '+27 82 896 9776', '+49 1525 4686401', '+27 72 250 8057', '+27 82 730 8426', '+27 72 268 5444', '+27 79 888 2983', '+27 71 473 6777', '+27 78 147 4533', '+27 73 294 4279', '+27 72 200 3152', '+27 61 342 8004', '+27 82 569 6732', '+27 83 644 6256', '+27 60 570 8688', '+27 73 120 0247', '+27 61 924 5133', '+27 82 895 8214', '+27 82 500 7575', '+27 82 968 7650', '+27 73 191 5974', '+27 72 878 0777', '+27 72 731 2385', '+27 82 454 4293', '+27 74 105 7634', '+27 71 843 2732', '+27 83 569 1785', '+27 76 765 4990', '+27 79 891 0726', '+27 83 648 7115', '+27 84 823 1407', '+27 61 025 7217', '+27 79 926 3236', '+31 6 39246886', '+27 84 548 2588', '+27 82 520 2118', '+27 60 526 3989', '+27 72 276 7882', '+27 84 988 8009', '+27 83 563 8250', '+49 1520 4696098', '+27 82 455 5997', '+27 66 223 5708', '+27 72 597 0297', '+27 76 478 3527', '+27 76 546 9207', '+27 79 883 6590', '+27 83 793 1293', '+44 7510 033159', '+27 76 536 4955', '+27 82 327 0796', '+27 76 777 2696', '+27 84 872 3364', '+27 79 798 8558', '+27 76 296 0760', '+27 84 451 1077', '+27 83 271 1500', '+27 82 671 6389', '+27 72 745 1130', '+27 73 102 0363', '+27 83 790 2536', '+27 81 430 3822', '+27 82 969 7286', '+27 82 602 0629', '+27 76 867 1859', '+27 79 832 2255', '+27 76 461 1826', '+27 83 234 6500', '+27 72 438 8496', '+27 82 446 4421', '+27 83 630 2779', '+263 71 334 1032', '+27 82 887 4759', '+27 72 250 0499', '+44 7760 998808', '+27 81 327 5680', '+27 82 468 8326', '+27 83 610 1720', '+27 82 660 5505', '+27 82 585 6424', '+27 82 529 1870', '+27 79 911 0065', '+27 82 929 7015', '+27 82 491 0513', '+27 84 413 4627', '+27 71 898 2677', '+27 79 433 2451', '+27 71 897 3483', '+27 82 566 3708', '+27 72 222 2006', '+27 82 530 1161', '+27 82 974 1847', '+27 79 492 1808', '+27 64 977 4301', '+27 79 075 2000', '+27 61 448 3168', '+27 83 652 5174', '+27 82 782 4655', '+27 73 225 6428', '+27 82 387 4046', '+31 6 22845631', '+27 82 417 7501', '+27 76 381 1235', '+27 82 335 9000', '+27 79 174 0483', '+27 73 348 8702', '+27 82 718 4043', '+27 71 644 6586', '+27 72 170 6082', '+27 71 755 1881', '+27 82 925 3598', '+27 79 375 4585', '+27 78 120 2558', '+27 81 560 1784', '+27 72 868 0428', '+44 7522 759951', '+27 78 186 3014', '+27 83 414 5764', '+27 76 488 8118', '+27 72 405 4400', '+27 72 574 4772', '+27 83 462 4125', '+230 5941 6327', '+27 83 402 5563', '+27 84 957 0353']

        # new_user_contacts = self._get_new_user_contacts()
        # print(new_user_contacts)
        new_user_contacts = ['Feedback ***REMOVED***', '+27 82 528 3606', '+27 83 260 8668', '+27 76 252 7652', '+27 76 250 0887', '+27 83 778 7509', '+27 81 267 3222', '+27 83 792 5465', '+27 73 404 1104', '+27 82 975 4217', '+27 82 702 2246', '+27 84 400 1210', '+27 71 572 5988', '+27 74 588 7141', '+27 72 257 7040', '+27 73 136 6159', '+27 82 443 4370', '+27 81 431 0160', '+44 7378 779994', '+27 79 667 7145', '+27 76 807 9417', '+27 76 082 5122', '+27 83 575 1500', '+27 71 147 2303', '+27 82 296 6008', '+27 76 212 2765', '+27 73 315 4037', '+27 74 187 1076', '+27 73 318 4090', '+27 83 661 4949', '+27 82 491 6895', '+27 79 553 8995', '+27 73 231 3174', '+27 83 408 3989', '+27 84 016 9284', '+27 82 462 0311', '+27 79 933 6834', '+27 76 106 1323', '+27 83 238 5352', '+44 7876 582807', '+27 62 252 0829', '+27 76 132 7953', '+27 83 661 2183', '+27 82 490 4987', '+27 71 562 4454', '+27 78 469 0640', '+27 71 112 5019', '+27 82 920 9149', '+44 7464 729094', '+27 83 268 0989', '+27 72 390 0355', '+27 73 271 9904', '+27 82 429 6648', '+27 72 974 4829', '+27 72 161 2246', '+27 72 483 3380', '+27 72 432 1693', '+27 83 616 4079', '+27 72 206 6950', '+27 84 088 6666', '+27 83 640 8579', '+44 7400 440812', '+27 83 656 8733', '+27 82 788 2727', '+27 79 772 2103', '+44 7957 419576', '+27 83 327 5415', '+27 71 686 3942', '+27 76 908 9433', '+267 71 875 500', '+27 76 194 2579', '+27 78 457 3287', '+27 72 143 0675', '+27 73 934 9659', '+27 83 708 1723', '+27 83 320 8073', '+27 82 532 8465', '+27 72 587 9780', '+27 82 086 3837', '+27 71 293 6757', '+27 82 551 8551', '+27 76 526 2701', '+27 82 373 3877', '+27 81 021 2674', '+27 71 134 5959', '+27 72 593 6289', '+27 76 339 0188', '+27 82 886 6547', '+27 76 953 0439', '+27 73 317 8687', '+27 82 926 4785', '+27 76 814 5942', '+27 71 689 1123', '+27 76 393 2587', '+27 78 218 8486', '+27 71 680 5981', '+27 71 166 7285', '+27 72 515 9543', '+27 79 802 8575', '+27 82 803 7676', '+27 72 267 0470', '+27 79 469 0607', '+27 82 049 5058', '+27 74 444 1588', '+27 83 254 9821', '+27 79 990 6644', '+1 (847) 804-2182', '+27 76 276 8066', '+27 73 050 4615', '+27 82 070 7061', '+27 82 484 4194', '+27 72 703 5447', '+27 62 331 9096', '+27 82 451 8041', '+27 84 653 0621', '+27 78 119 9259', '+27 60 942 1590', '+27 71 414 8477', '+1 (612) 598-5133', '+27 84 083 0245', '+27 83 400 0214', '+27 83 778 1928', '+27 73 097 5938', '+27 83 723 4760', '+27 76 786 8246', '+27 76 428 0891', '+27 83 503 3556', '+27 82 072 9359', '+86 186 8931 3044', '+27 72 218 8240', '+27 82 444 9310', '+27 83 377 1625', '+27 84 562 1289', '+27 82 921 0904', '+27 83 470 0033', '+27 83 646 8924', '+27 73 958 3665', '+27 83 629 3806', '+27 76 680 8943', '+27 72 623 5374', '+27 84 957 0353']
        print(len(new_user_contacts))
        print('Checking for new users')
        while True:
            if not new_user_contacts:
                break
            for number in new_user_contacts:
                if self.try_search_for_contact(number):
                    # conversation = self._find_conversation_by_id(number)
                    # self._process_conversation(conversation)
                    messages_panel = self.wait.until(lambda _: self.driver.find_element_by_xpath("//div[@class='_9tCEa']"))
                    username = self._process_new_user(messages_panel)
                    if username:
                        print('New user %s ~ %s' % (username, number))
                        new_uid = self._create_new_user(contact_number=number, username=username)
                        if new_uid:
                            print('Successfully created user: %s' % new_uid)
                        else:
                            print('Failed to create user: %s' % number)
                            continue
                    else:
                        print('No valid launch sequence for %s' % number)
                        continue
                    new_user_contacts.remove(number)
                    print(new_user_contacts)
                else:
                    print('Couldnt find contact')
            # scroll_progress = self._side_pane_scroll_top()
            # scroll_max = self._side_pane_scroll_top_max()
            # if scroll_progress == scroll_max:
            #     self._side_pane_scroll_to(0)
            # else:
            #     self._side_pane_scroll_by(500)

        # self.processed_contacts = list(map(lambda contact: self._clean_contact_number(contact), self.processed_contacts))
        # self.processed_contacts = list(filter(None.__ne__, self.processed_contacts))
        #
        # for number in self.processed_contacts:
        #     print('Number: %s _ %s' % (number, self._get_uid_from_number(number)))
        # print(self.processed_contacts)

    def send_welcome_message(self, contact_id):
        message = "Welcome to ***REMOVED*** my bok boks"
                  # "\n\nWe’re still in the testing phase " \
                  # "(we even have to use Dom & Josh’s voices for now, bless them)," \
                  # " so if you have any feedback or need help message this ***REMOVED*** number %s" \
                  # "\n\nEach Thursday morning we send out your ***REMOVED***, via a mp3 file and a link. " \
                  # "The link let’s you listen on our web app where you can customise your ***REMOVED*** %s" \
                  # "\n\nThanks for being curious my special person!" \

        params = {
            'number': contact_id,
            'message': message,
        }

        headers = {
            'X-Auth-Token': os.environ['AUTH_TOKEN']
        }

        req = requests.get("http://localhost:8001/message", params=params, headers=headers)

        if req.status_code == 200:
            print('Message delivered to %s' % contact_id)
            print('%s %s' % (req.status_code, req.reason))
            return True
        else:
            print('Message failed to deliver to %s' % contact_id)
            print('%s %s' % (req.status_code, req.reason))
            return False

    def _get_new_user_contacts(self):
        new_user_contacts = []
        for number in self.processed_contacts:
            uid = self.get_uid_from_number_db(number)
            if uid:
                print('Existing user: %s' % uid)
                continue
            else:
                uid = self._get_uid_from_number(number)
            if not uid:
                print('New user: %s' % number)
                new_user_contacts.append(number)
        return new_user_contacts

    def _clean_contact_number(self, contact_number):
        contact_number = contact_number.replace(' ', '')
        if self._is_valid_numeric(contact_number):
            return contact_number
        else:
            return None

    def _is_valid_numeric(self, string):
        for char in string:
            if char.isdigit() or char == '+':
                continue
            else:
                return False
        return True

    def _get_uid_from_number(self, contact_number):
        data = {
            'content-type': 'application/json',
            'fullMobileNum': contact_number
        }

        headers = {
            'Authorization': '56128eebf5a64cb6875b8d1c4789b216cf2331aa',
            'Origin': 'https://my***REMOVED***.com'
        }

        req = requests.post("***REMOVED***:3000/user_uid_from_full_mobile_num", data=data, headers=headers)

        if req.status_code == 200:
            return req.json()['userUID']
        else:
            print(req.status_code, req.reason)
            return None

    def _create_new_user(self, contact_number, username=None):
        data = {
            'Content-Type': 'application/json',
            'fullMobileNum': contact_number,
            'username': username
        }

        headers = {
            'Authorization': '***REMOVED***',
            'Origin': 'http://my***REMOVED***.com'
        }

        req = requests.post("http://***REMOVED***-client-api.fzg22nmp77.us-east-2.elasticbeanstalk.com/users/create_user_full_num", data=data, headers=headers)

        if req.status_code == 200:
            return req.json()['userUID']
        else:
            print(req.status_code, req.reason)
            return None

    def process_messages(self):
        self._for_each_conversation(self._process_conversation)

    def _for_each_conversation(self, func):
        print('Ensuring connection okay')
        # self.session.wait_until_connection_okay()

        print('Fetching conversations panel')
        conversations_panel: WebElement = self._get_conversations_panel()
        print('Fetching conversations')
        conversations: [WebElement] = lambda: conversations_panel.find_elements_by_class_name('_2wP_Y')

        print('Processing conversations')
        while True:
            def sorted_conversations(): return sorted(conversations(), key=lambda el: self._get_element_y_position(el))
            conversations_copy = sorted_conversations().copy()
            # print(list(map(lambda conv: '%s ~ %s' % (conv.id, conv.text), conversations_copy)))
            for index in range(len(conversations_copy)):
                func(conversations_copy[index])

            scroll_progress = self._side_pane_scroll_top()
            scroll_max = self._side_pane_scroll_top_max()
            if scroll_progress == scroll_max:
                break

            last_processed_conversation = conversations_copy[-1]
            self._scroll_into_view(last_processed_conversation, True)
            time.sleep(0.1)

            progress = round((scroll_progress/scroll_max)*100)
            print('Progress: %s' % progress)

    def _process_contact(self, conversation: WebElement):
        contact_name_number = self.wait.until(lambda _: conversation.find_element_by_xpath(".//span[@class='_1wjpf']")) \
            .get_attribute('title')

        if contact_name_number not in self.processed_contacts:
            self.processed_contacts.append(contact_name_number)

        return contact_name_number

    def _process_conversation(self, conversation: WebElement):
        print('\nProcessing conversation...')
        uid = None
        try:
            # Assuming the user is not saved as a contact, 'contact_id' will return the number
            contact_id = self.wait.until(lambda _: conversation.find_element_by_xpath(".//span[@class='_1wjpf']")) \
                .get_attribute('title')

            contact_id = self._clean_contact_number(contact_id)
            if not contact_id:
                print('Invalid contact ID')
                return False

            # Try get uid from local database, otherwise perform network call,
            # if this fails then user needs to be created first
            uid = self.get_uid_from_number_db(contact_id)
            if not uid:
                uid = self._get_uid_from_number(contact_id)
            if not uid:
                print('User needs to be created')

            last_message_content = self.wait.until(lambda _: conversation.find_element_by_xpath(".//span[@class='_2_LEW']")) \
                .get_attribute('title')

            last_message = WhatsAppMessage(uid=uid, timestamp=None, sender_name=None, sender_number=contact_id, content=last_message_content)
            del last_message.timestamp
            del last_message.sender_name

            if self.messages_in_sync(last_message):
                print('Messages in sync')
                return True

            print('Processing conversation %s: ID - %s' % (conversation.id, contact_id))
        except NoSuchElementException:
            print('No such element')
            return False

        messages_panel = self.load_conversation_messages_panel(conversation)
        self.previous_conversation_content = messages_panel

        if uid:
            # messages = self._extract_and_save_messages(messages_panel)
            # print('Saving messages to database')
            # for message in messages:
            #     message.uid = uid
            #     self.save_message(message)
            #     print('Message: %s' % message.__dict__)
            return True
        else:
            username = self._process_new_user(messages_panel)
            if username:
                print('New user %s ~ %s' % (username, contact_id))
                new_uid = self._create_new_user(contact_number=contact_id, username=username)
                if new_uid:
                    print('Successfully created user: %s' % new_uid)
                else:
                    print('Failed to create user: %s' % contact_id)
            else:
                print('No valid launch sequence for %s' % contact_id)
            return False

    def load_conversation_messages_panel(self, conversation):

        self.wait.until(lambda _: conversation and conversation.is_displayed() and conversation.is_enabled())
        while True:
            try:
                conversation.click()
                break
            except ElementClickInterceptedException:
                time.sleep(0.1)
                continue

        # If moving from active conversation, wait for content to refresh after click
        # while True:
        #     self.wait.until(lambda _: conversation and conversation.is_displayed() and conversation.is_enabled())
        #     conversation.click()
        #     try:
        #         conversation.click()
        #         break
        #     except ElementClickInterceptedException:
        #         self._scroll_into_view(conversation, False)
        #         continue

        if self.previous_conversation_content:
            self.wait.until(exp_c.staleness_of(self.previous_conversation_content))

        messages_panel = self.wait.until(lambda _: conversation.find_element_by_xpath("//div[@class='_9tCEa']"))
        # self.wait.until(
        #     lambda _: 'loading' not in messages_panel.find_element_by_class_name('_3dGYA').get_attribute('title'))

        # Scroll through all messages until 100 messages are scraped, or we reach the top
        try:
            while len(messages_panel.find_elements_by_class_name('vW7d1')) < MESSAGE_LIMIT:
                try:
                    load_spinner = WebDriverWait(self.driver, 2) \
                        .until(lambda _: self.driver.find_element_by_xpath("//div[@class='_3dGYA']"))
                    self._scroll_into_view(load_spinner, True)
                except (TimeoutException, StaleElementReferenceException):
                    break
                self.wait.until(lambda _: not self._messages_are_loading())
        except NoSuchElementException:
            pass

        return messages_panel

    def _scroll_into_view(self, web_element, align_top: bool):
        return self.driver.execute_script('return arguments[0].scrollIntoView(%s);' % 'true' if align_top else 'false', web_element)

    def _get_element_y_position(self, web_element):
        return self.driver.execute_script('return arguments[0].getBoundingClientRect().top;', web_element)

    def _scroll_top(self, web_element):
        return self.driver.execute_script('return arguments[0].scrollTop;', web_element)

    def _scroll_top_max(self, web_element):
        return self.driver.execute_script('return arguments[0].scrollTopMax;', web_element)

    def _side_pane_scroll_top(self):
        side_pane = self.driver.find_element_by_id('pane-side')
        return self._scroll_top(side_pane)

    def _side_pane_scroll_top_max(self):
        side_pane = self.driver.find_element_by_id('pane-side')
        return self._scroll_top_max(side_pane)

    def _side_pane_scroll_by(self, pixels):
        side_pane = self.driver.find_element_by_id('pane-side')
        return self.driver.execute_script('return arguments[0].scrollBy(0, %d);' % pixels, side_pane)

    def _side_pane_scroll_to(self, pixels):
        side_pane = self.driver.find_element_by_id('pane-side')
        return self.driver.execute_script('return arguments[0].scrollTo(0, %d);' % pixels, side_pane)

    def _messages_are_loading(self):
        try:
            def load_spinner(): self.driver.find_element_by_xpath("//div[@class='_3dGYA']")
            if load_spinner():
                return 'loading' in load_spinner().get_attribute('title')
            else:
                return False
        except NoSuchElementException:
            return False

    def _get_conversations_panel(self):
        conversations_panel = None
        try:
            conversations_panel = self.wait.until(
                exp_c.visibility_of_element_located((By.XPATH, "//div[@class='RLfQR']")))
        except TimeoutException:
            pass
        return conversations_panel

    def _find_conversation_by_id(self, contact_id):
        conversations_panel: WebElement = self._get_conversations_panel()
        try:
            return conversations_panel.find_element_by_xpath(".//span[@class='_1wjpf'][@title='%s']/ancestor::div[@class='_2wP_Y']" % contact_id)
        except NoSuchElementException:
            return None

    def try_search_for_contact(self, contact_number):
        # Enter search text
        try:
            search_bar = WebDriverWait(self.driver, TIMEOUT).until(
                exp_c.visibility_of_element_located((By.XPATH, "//input[@class='jN-F5 copyable-text selectable-text']"))
            )
            search_bar.click()
            search_bar.send_keys(contact_number)
            print('Searching for contact ' + contact_number)
        except (ElementClickInterceptedException, TimeoutException):
            return False
        # Wait for finished loading
        try:
            clear_search = self.wait.until(lambda _: self.driver.find_element_by_xpath("//button[@class='_3Burg']"))
        except TimeoutException:
            return False
        # If no contacts found, return False
        try:
            self.driver.find_element_by_xpath("//div[@class='_3WZoe']")
            print('No contacts found')
            return False
        except NoSuchElementException:
            print('Contact found')
            pass
        # Else Press enter
        try:
            if search_bar:
                print('Selecting contact conversation')
                search_bar.send_keys(Keys.RETURN)
                clear_search.click()
        except ElementClickInterceptedException:
            return False
        # Check contact header for correct number
        try:
            print('Waiting for contact header')
            contact_header = self.wait.until(lambda _: self.driver.find_element_by_xpath("//header[@class='_3AwwN']"))
        except TimeoutException:
            return False
        try:
            print('Fetching contact ID')
            contact_id = self.wait.until(lambda _: contact_header.find_element_by_xpath(".//span[@class='_1wjpf']")) \
                .get_attribute('title')
        except TimeoutException:
            return False

        print('Contact ID %s ~ Contact number %s' % (contact_id, contact_number))
        if contact_id and contact_number and (contact_id.replace(" ", "") == "%s" % contact_number.replace(" ", "")):
            return True
        else:
            return False

    def _extract_and_save_messages(self, messages_panel):
        messages: [WhatsAppMessage] = []

        def append_message(message): messages.append(message)
        self._for_each_message(messages_panel, append_message)

        return messages

    def _process_new_user(self, messages_panel):
        messages: [WhatsAppMessage] = []
        username = None

        def append_message(msg): messages.append(msg)
        self._for_each_message(messages_panel, append_message)

        for message in messages:
            # Split message content into words
            word_list = message.content.split()
            # Strip whitespace
            word_list = [word.strip() for word in word_list]

            # Find launch words
            launch_words = list(filter(lambda word: self.similar('launch', word.lower(), 0.7)
                                or self.similar('start', word.lower(), 0.7), word_list))

            if not launch_words or not message.content.strip().startswith(launch_words[0]):
                continue

            # Remove launch words
            word_list = [word for word in word_list if word not in launch_words]

            # Remaining words should be name and surname
            if not word_list:
                continue

            name, *surname = word_list
            username = " ".join(word_list)
            # Remove non-alpha characters
            username = "".join([c for c in username if c.isalpha() or c.isspace()])

            if username:
                return username

        return username

    def similar(self, a, b, threshold):
        return SequenceMatcher(None, a, b).ratio() >= threshold

    def _for_each_message(self, messages_panel, func):
        message_elements: [WebElement] = lambda: messages_panel \
            .find_elements_by_xpath(".//div[@class='vW7d1'][position() <= %d]" % MESSAGE_LIMIT)

        number_elements = len(message_elements())
        for index in range(number_elements):
            try:
                details_el: WebElement = message_elements()[index] \
                    .find_element_by_xpath(".//div[@class='Tkt2p']/div[1]")
            except NoSuchElementException:
                try:
                    details_el: WebElement = message_elements()[index] \
                        .find_element_by_xpath(".//div[@class='Tkt2p']/div[2]")
                except NoSuchElementException:
                    continue
            details = details_el.get_attribute('data-pre-plain-text')

            if details:
                time_string: str = details[details.find('[')+1:details.find(']')]
                sender_id: str = details.replace('[%s]' % time_string, '', 1).strip().replace(':', '', 1)
            else:
                continue

            # content: str = self.wait.until(lambda x: message_elements()[index].find_element_by_xpath(
            #     ".//span[@class='selectable-text invisible-space copyable-text']")).text
            try:
                content: str = message_elements()[index].find_element_by_xpath(
                    ".//span[@class='selectable-text invisible-space copyable-text']").text
            except NoSuchElementException:
                continue

            message = self.create_message('', time_string=time_string, sender_name=None,
                                          sender_number=sender_id, content=content)
            func(message)

    def create_message(self, uid, time_string, sender_name, sender_number, content):
        # Time string format: [18:44, 7/8/2018]
        # See http://strftime.org/
        # Timestamp can change, so using dateutil instead
        # timestamp = datetime.datetime.strptime(time_string, "%H:%M, %m/%d/%Y").replace(tzinfo=datetime.timezone.utc)

        timestamp = dateutil.parser.parse(time_string).replace(tzinfo=datetime.timezone.utc)
        msg = WhatsAppMessage(uid, timestamp, sender_name, sender_number, content)

        return msg

    def save_message(self, msg: WhatsAppMessage):
        # message_json = json.dumps(msg.__dict__, indent=4, sort_keys=True, default=str)
        # message_json = dumps(msg.__dict__)

        # Insert object into messages_collection and log database id
        try:
            schedule_id = self.messages_collection.insert_one(msg.__dict__).inserted_id
            print('Message inserted in database with ID ' + str(schedule_id))
            return schedule_id
        except WriteError:
            print('Duplicate message exists in database')
            return None

    def delete_message(self, msg_id):
        print('Deleting message from database')
        self.messages_collection.delete_many({"_id": msg_id})

    def purge_all_messages(self):
        print('Deleting all messages from database')
        self.messages_collection.delete_many({})

    def get_uid_from_number_db(self, contact_number):
        message = self.messages_collection.find_one({'sender_number': contact_number})
        if message:
            return message['uid']
        else:
            return None

    def messages_in_sync(self, last_message: WhatsAppMessage):
        last_message_dict = last_message.__dict__
        if self.messages_collection.find_one(last_message_dict):
            return True
        else:
            return False


def debug():
    print('Procesing WhatsApp conversations')
    whatsapp_receive = WhatsAppReceive()
    # print(whatsapp_receive._get_uid_from_number('+27763381243'))
    # whatsapp_receive.process_contacts()
    # whatsapp_receive.process_messages()

    # new_user_contacts = ['+27 61 025 7217', '+27 83 790 2536', '+27 74 475 9415', '+27 82 569 6732', '+27 83 234 6500', '+27 72 552 9500', '+27 72 086 3377', '+27 78 147 4533', '+27 79 690 0576', '+27 72 452 6334', '+27 73 598 7254', '+27 71 851 6687', '+27 83 569 1785', '+27 63 887 7920', '+27 76 299 7577', '+27 72 117 4999', '+27 84 847 7666', '+27 82 454 4293', '+27 82 574 7645', '+27 76 488 8118', '+27 63 245 9335', '+27 76 765 3373', '+27 82 505 0944', '+27 72 878 0777', '+27 66 268 4344', '+27 83 225 5305', '+27 82 782 4655', '+27 76 555 9180', '+254 729 406636', '+27 83 586 3979', '+27 84 903 4239', '+27 79 174 0483', '+27 72 117 4645', '+27 84 988 8009', '+27 83 782 1847', '+27 72 170 6082', '+27 76 339 2072', '+27 82 520 2118', '+27 82 718 4043', '+27 71 403 9117', '+27 72 268 5444', '+27 72 271 5617', '+27 79 883 6590', '+44 7747 455486', '+27 72 879 6256', '+27 82 083 1791', '+27 82 789 5023', '+27 82 726 5477', '+27 72 868 0428', '+27 83 644 6256', '+27 60 526 3989', '+27 83 641 9768', '+27 78 185 4892', '+27 83 610 1720', '+27 83 695 0440', '+27 82 616 1888', '+27 83 563 8250', '+230 5939 9446', '+27 73 281 4936', '+27 76 473 8036', '+27 84 548 4828', '+27 84 957 0353']
    #
    # for contact in new_user_contacts:
    #     whatsapp_receive.send_welcome_message(contact)

    whatsapp_receive.send_welcome_message('+27 76 338 1243')


if __name__ == '__main__':
    print('Procesing WhatsApp conversations')
    whatsapp_receive = WhatsAppReceive()
    # print(whatsapp_receive._get_uid_from_number('+27763381243'))
    whatsapp_receive.process_contacts()
    # whatsapp_receive.process_messages()

    # new_user_contacts = ['Feedback ***REMOVED***', '+27 82 528 3606', '+27 83 260 8668', '+27 76 252 7652', '+27 76 250 0887', '+27 83 778 7509', '+27 81 267 3222', '+27 83 792 5465', '+27 73 404 1104', '+27 82 975 4217', '+27 82 702 2246', '+27 84 400 1210', '+27 71 572 5988', '+27 74 588 7141', '+27 72 257 7040', '+27 73 136 6159', '+27 82 443 4370', '+27 81 431 0160', '+44 7378 779994', '+27 79 667 7145', '+27 76 807 9417', '+27 76 082 5122', '+27 83 575 1500', '+27 71 147 2303', '+27 82 296 6008', '+27 76 212 2765', '+27 73 315 4037', '+27 74 187 1076', '+27 73 318 4090', '+27 83 661 4949', '+27 82 491 6895', '+27 79 553 8995', '+27 73 231 3174', '+27 83 408 3989', '+27 84 016 9284', '+27 82 462 0311', '+27 79 933 6834', '+27 76 106 1323', '+27 83 238 5352', '+44 7876 582807', '+27 62 252 0829', '+27 76 132 7953', '+27 83 661 2183', '+27 82 490 4987', '+27 71 562 4454', '+27 78 469 0640', '+27 71 112 5019', '+27 82 920 9149', '+44 7464 729094', '+27 83 268 0989', '+27 72 390 0355', '+27 73 271 9904', '+27 82 429 6648', '+27 72 974 4829', '+27 72 161 2246', '+27 72 483 3380', '+27 72 432 1693', '+27 83 616 4079', '+27 72 206 6950', '+27 84 088 6666', '+27 83 640 8579', '+44 7400 440812', '+27 83 656 8733', '+27 82 788 2727', '+27 79 772 2103', '+44 7957 419576', '+27 83 327 5415', '+27 71 686 3942', '+27 76 908 9433', '+267 71 875 500', '+27 76 194 2579', '+27 78 457 3287', '+27 72 143 0675', '+27 73 934 9659', '+27 83 708 1723', '+27 83 320 8073', '+27 82 532 8465', '+27 72 587 9780', '+27 82 086 3837', '+27 71 293 6757', '+27 82 551 8551', '+27 76 526 2701', '+27 82 373 3877', '+27 81 021 2674', '+27 71 134 5959', '+27 72 593 6289', '+27 76 339 0188', '+27 82 886 6547', '+27 76 953 0439', '+27 73 317 8687', '+27 82 926 4785', '+27 76 814 5942', '+27 71 689 1123', '+27 76 393 2587', '+27 78 218 8486', '+27 71 680 5981', '+27 71 166 7285', '+27 72 515 9543', '+27 79 802 8575', '+27 82 803 7676', '+27 72 267 0470', '+27 79 469 0607', '+27 82 049 5058', '+27 74 444 1588', '+27 83 254 9821', '+27 79 990 6644', '+1 (847) 804-2182', '+27 76 276 8066', '+27 73 050 4615', '+27 82 070 7061', '+27 82 484 4194', '+27 72 703 5447', '+27 62 331 9096', '+27 82 451 8041', '+27 84 653 0621', '+27 78 119 9259', '+27 60 942 1590', '+27 71 414 8477', '+1 (612) 598-5133', '+27 84 083 0245', '+27 83 400 0214', '+27 83 778 1928', '+27 73 097 5938', '+27 83 723 4760', '+27 76 786 8246', '+27 76 428 0891', '+27 83 503 3556', '+27 82 072 9359', '+86 186 8931 3044', '+27 72 218 8240', '+27 82 444 9310', '+27 83 377 1625', '+27 84 562 1289', '+27 82 921 0904', '+27 83 470 0033', '+27 83 646 8924', '+27 73 958 3665', '+27 83 629 3806', '+27 76 680 8943', '+27 72 623 5374', '+27 84 957 0353']
    # print(len(new_user_contacts))
    #
    # for contact in new_user_contacts:
    #     whatsapp_receive.send_welcome_message(contact)
