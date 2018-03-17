class Inception(nn.Module):
    def __init__(self, in_channels, k_1x1, k_3x3red, k_3x3, k_5x5red, k_5x5, pool_proj):
        super(Inception, self).__init__()
        self.b1 = nn.Sequential(
            nn.Conv2d(in_channels=in_channels, out_channels=k_1x1, kernel_size=1),
            nn.ReLU(inplace=True)
        )
        self.b2 = nn.Sequential(
            nn.Conv2d(in_channels=in_channels, out_channels=k_3x3red, kernel_size=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(in_channels=k_3x3red, out_channels=k_3x3, kernel_size=3, padding=1),
            nn.ReLU(inplace=True)
        )
        self.b3 = nn.Sequential(
            nn.Conv2d(in_channels=in_channels, out_channels=k_5x5red, kernel_size=1, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(in_channels=k_5x5red, out_channels=k_5x5, kernel_size=5, padding=1),
            nn.ReLU(inplace=True)
        )
        self.b4 = nn.Sequential(
            nn.MaxPool2d(kernel_size=3, stride=1),
            nn.Conv2d(in_channels=in_channels, out_channels=pool_proj, kernel_size=1, padding=1),
            nn.ReLU(inplace=True)
        )
    def forward(self, x):
        y1 = self.b1(x)
        y2 = self.b2(x)
        y3 = self.b3(x)
        y4 = self.b4(x)
        return(torch.cat([y1, y2, y3, y4], 1))

class AuxClassifier(nn.Module):
    def __init__(self, num_classes, in_channels):
        super(AuxClassifier, self).__init__()
        self.pool1 = nn.AvgPool2d(kernel_size=5, stride=3)
        self.conv1 = nn.Sequential(
            nn.Conv2d(in_channels=in_channels, out_channels=128, kernel_size=1),
            nn.ReLU(inplace=True)
        )
        
        self.fc1 = nn.Sequential(
            nn.Linear(in_features=4 * 4 * 128, out_features=1024),
            nn.ReLU(inplace=True)
        )
        self.drop = nn.Dropout(p=0.3)
        self.fc2 = nn.Linear(in_features=1024, out_features=num_classes)
    def forward(self, x):
        x = self.pool1(x)
        x = self.conv1(x)
        x = x.view(x.size(0), -1)
        x = self.fc1(x)
        x = self.drop(x)
        x = self.fc2(x)
        return(x)       

class GoogLeNet(nn.Module):
    def __init__(self, num_classes, aux_classifier=True):
        super(GoogLeNet, self).__init__()
        self.aux_classifier = aux_classifier
        self.head = nn.Sequential(
            nn.Conv2d(in_channels=3, out_channels=64, kernel_size=7, stride=2, padding=3),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
            nn.Conv2d(in_channels=64, out_channels=64, kernel_size=1, stride=1, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(in_channels=64, out_channels=192, kernel_size=3, stride=1, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2)
        )
        
        self.block3a = Inception(in_channels=192, k_1x1=64, k_3x3red=96, k_3x3=128, k_5x5red=16, k_5x5=32, pool_proj=32)
        self.block3b = Inception(in_channels=256, k_1x1=128, k_3x3red=128, k_3x3=192, k_5x5red=32, k_5x5=96, pool_proj=64)
        self.pool1 = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.block4a = Inception(in_channels=480, k_1x1=192, k_3x3red=96, k_3x3=208, k_5x5red=16, k_5x5=48, pool_proj=64)
        if aux_classifier:
            self.aux0 = AuxClassifier(num_classes=num_classes, in_channels=512)
        self.block4b = Inception(in_channels=512, k_1x1=160, k_3x3red=112, k_3x3=224, k_5x5red=24, k_5x5=64, pool_proj=64)
        self.block4c = Inception(in_channels=512, k_1x1=128, k_3x3red=128, k_3x3=256, k_5x5red=24, k_5x5=64, pool_proj=64)
        self.block4d = Inception(in_channels=512, k_1x1=112, k_3x3red=144, k_3x3=288, k_5x5red=32, k_5x5=64, pool_proj=64)
        if aux_classifier:
            self.aux1 = AuxClassifier(num_classes=num_classes, in_channels=528)
        self.block4e = Inception(in_channels=528, k_1x1=256, k_3x3red=160, k_3x3=320, k_5x5red=32, k_5x5=128, pool_proj=128)
        self.pool2 = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.block5a = Inception(in_channels=832, k_1x1=256, k_3x3red=160, k_3x3=320, k_5x5red=32, k_5x5=128, pool_proj=128)
        self.block5b = Inception(in_channels=832, k_1x1=384, k_3x3red=192, k_3x3=384, k_5x5red=48, k_5x5=128, pool_proj=128)
        self.pool3 = nn.AvgPool2d(kernel_size=7, stride=1)
        self.drop = nn.Dropout(p=0.4)
        self.classifier = nn.Linear(in_features=1024, out_features=num_classes)
        self._initialize_weights()

    def forward(self, x):
        x = self.head(x)
        x = self.block3a(x)
        x = self.block3b(x)
        x = self.pool1(x)
        x = self.block4a(x)
        if self.training and self.aux_classifier:
            output0 = self.aux0(x)
        x = self.block4b(x)
        x = self.block4c(x)
        x = self.block4d(x)
        if self.training and self.aux_classifier:
            output1 = self.aux1(x)
        x = self.block4e(x)
        x = self.pool2(x)
        x = self.block5a(x)
        x = self.block5b(x)
        x = self.pool3(x)
        x = x.view(x.size(0), -1)
        x = self.drop(x)
        output2 = self.classifier(x)
        return(output0, output1, output2)

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, math.sqrt(2. / n))
                if m.bias is not None:
                    m.bias.data.zero_()
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()
            elif isinstance(m, nn.Linear):
                m.weight.data.normal_(0, 0.01)
                m.bias.data.zero_()
